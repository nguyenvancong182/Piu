# Hướng dẫn Test Ứng dụng Piu

## 🎯 Mục đích
Đảm bảo ứng dụng Piu vẫn chạy bình thường sau khi tạo cấu trúc mới.

---

## ✅ Bước 1: Kiểm tra File Gốc

File `Piu.py` vẫn còn nguyên, chưa được refactor:

```bash
# Xem file
dir Piu.py

# Kích thước: ~2.5MB (2,533,689 bytes)
# Đây là file gốc, chưa bị thay đổi
```

---

## ✅ Bước 2: Chạy Ứng dụng Gốc

### Cách 1: Chạy bằng Python
```bash
python Piu.py
```

### Cách 2: Double-click file (nếu đã package thành .exe)
```
Double-click vào Piu.py trong file explorer
```

### Cách 3: Sử dụng VS Code/Cursor
```
Right-click Piu.py → Run Python File in Terminal
```

---

## ✅ Bước 3: Test Các Chức Năng

Khi ứng dụng mở, hãy test các chức năng chính:

### 1. **Tab Download**
- [ ] Thử tải một video YouTube đơn giản
- [ ] Kiểm tra hàng chờ hoạt động
- [ ] Xem log hiển thị

### 2. **Tab Subtitle**
- [ ] Load một file video
- [ ] Test tạo subtitle bằng Whisper
- [ ] Xem kết quả

### 3. **Tab Dubbing**
- [ ] Add một task vào queue
- [ ] Chọn giọng TTS
- [ ] Test generate audio

### 4. **Tab Upload**
- [ ] Test connect YouTube
- [ ] Upload metadata (nếu cần)

### 5. **Settings**
- [ ] Mở API Settings
- [ ] Mở Branding Settings
- [ ] Test save/load config

---

## ⚠️ Lưu ý

1. **Piu.py vẫn là file gốc** - Chưa được refactor
2. **Cấu trúc mới** chỉ mới setup folder, chưa sử dụng
3. **Logo files** đã được giữ ở thư mục gốc (không di chuyển vào assets/ vì Piu.py cần chúng ở đây)
4. **Nếu có lỗi** - Báo ngay để rollback

---

## 📝 Kết quả mong đợi

✅ Ứng dụng mở bình thường  
✅ Không có lỗi import  
✅ Tất cả chức năng hoạt động như cũ  
✅ Config được load/save bình thường  

---

## 🔧 Nếu có lỗi

Nếu gặp bất kỳ lỗi nào:

1. **Báo lỗi ngay**
2. **Screenshot error message**
3. Tạm ngừng refactor và fix lỗi trước

---

## 📦 Trạng thái hiện tại

- ✅ Piu.py gốc vẫn còn nguyên
- ✅ Cấu trúc mới đã setup xong
- ✅ Config/Constants đã tách ra
- ⏳ Chưa refactor code logic
- ⏳ Ứng dụng vẫn chạy từ Piu.py gốc

---

**🎉 Chúc test thành công!**

