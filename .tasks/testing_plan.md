# Kế hoạch Testing - Piu Application

**Ngày tạo:** 2025-01-XX  
**Mục tiêu:** Đảm bảo stability sau refactor, không có regression bugs

---

## Tổng quan

### Context
- ✅ Đã hoàn thành 5 bước refactor chính (AI, Image, Model, Metadata, YouTube services)
- ✅ Piu.py đã giảm từ ~31,000 xuống 26,764 lines (-13.6%)
- ✅ Tất cả services đã được tách và tích hợp
- ✅ Không có lỗi syntax/linter
- ⚠️ **Cần đảm bảo:** Không có regression bugs sau refactor

### Nguyên tắc Testing
1. **Focus vào integration tests** - Kiểm tra services hoạt động với Piu.py
2. **Smoke tests cho critical flows** - Đảm bảo main features hoạt động
3. **Manual validation** - Một số test cases phức tạp cần manual
4. **Progressive approach** - Bắt đầu đơn giản, dần tăng complexity

---

## Phase 1: Foundation (1-2 giờ) 🏗️

### 1.1 Setup Test Infrastructure
- [x] Tạo `tests/integration/` directory
- [x] Setup pytest với fixtures cơ bản
- [x] Tạo test helpers cho mocking services
- [x] Setup test data (sample files, configs)
- [x] Tạo `pytest.ini` configuration
- [x] Tạo `tests/README.md` với hướng dẫn

### 1.2 Basic Service Tests
Mục tiêu: Đảm bảo services khởi tạo và interface hoạt động

- [x] `tests/integration/test_services_init.py`
  - ✅ Test: AIService khởi tạo
  - ✅ Test: ImageService khởi tạo
  - ✅ Test: ModelService khởi tạo
  - ✅ Test: MetadataService khởi tạo
  - ✅ Test: YouTubeService khởi tạo
  
- [x] `tests/integration/test_youtube_service.py`
  - ✅ Test: YouTubeService khởi tạo
  - ✅ Test: add_task_to_queue
  - ✅ Test: remove_task_from_queue
  - ✅ Test: get_queue
  - ✅ Test: batch processing (start/stop/finish)
  - ✅ Test: title truncation
  
- [x] `tests/integration/test_ai_service.py` ✅ **DONE**
  - ✅ Test: test_gemini_key với invalid key
  - ✅ Test: test_openai_key với invalid key
  - ✅ Test: translate_with_openai error handling
  - ✅ Test: script processing error handling
  
- [x] `tests/integration/test_metadata_service.py` ✅ **DONE**
  - ✅ Test: load_cache với empty file
  - ✅ Test: load_cache với data
  - ✅ Test: save_cache
  - ✅ Test: get_metadata, has_metadata
  - ✅ Test: update_metadata (CRUD)
  - ✅ Test: auto-increment thumbnail
  - ✅ Test: autofill_youtube_fields
  - ✅ Test: get_title_from_filename

**Success criteria:** ✅ Tất cả services khởi tạo thành công

---

## Phase 2: Integration Tests (3-5 giờ) 🔗

### 2.1 Service Integration với Piu.py
Mục tiêu: Đảm bảo services tích hợp đúng với main app

- [ ] `tests/integration/test_ai_integration.py`
  - Test: translate_openai delegate sang AIService
  - Test: API key check flow
  
- [ ] `tests/integration/test_model_integration.py`
  - Test: Model loading flow
  - Test: CUDA detection integration
  
- [ ] `tests/integration/test_metadata_integration.py`
  - Test: Metadata cache load/save
  - Test: Autofill flow
  
- [ ] `tests/integration/test_youtube_integration.py`
  - Test: Queue management
  - Test: Batch processing state

**Success criteria:** ✅ Services được gọi đúng từ Piu.py

### 2.2 Critical Path Tests
Mục tiêu: Test main workflows của app

- [ ] Download → Subtitle workflow
  - Test: Download video từ URL
  - Test: Generate subtitle
  - Test: Save SRT file
  
- [ ] Dubbing workflow
  - Test: Generate TTS audio
  - Test: Mux audio với video
  
- [ ] AI processing workflow
  - Test: Gemini script editing (mock API)
  - Test: OpenAI translation (mock API)
  
- [ ] YouTube upload workflow
  - Test: Add to queue
  - Test: Batch processing logic

**Success criteria:** ✅ Main workflows hoạt động end-to-end

---

## Phase 3: Regression Tests (2-3 giờ) 🔍

### 3.1 UI State Tests
Mục tiêu: Đảm bảo UI state được quản lý đúng

- [ ] Test: Tab switching không mất state
- [ ] Test: Queue display updates correctly
- [ ] Test: Progress indicators work
- [ ] Test: Error handling displays properly

### 3.2 Edge Cases
Mục tiêu: Test các trường hợp boundary và error

- [ ] Empty queue handling
- [ ] Invalid file paths
- [ ] Network errors (mock)
- [ ] Missing API keys
- [ ] Large files handling
- [ ] Concurrent operations

---

## Phase 4: Manual Validation (1-2 giờ) 👤

### 4.1 Manual Smoke Tests
**Không thể automate được, cần manual test:**

- [ ] **Download Tab**
  - Download video từ YouTube (có cookie)
  - Download audio từ YouTube
  - Verify output quality
  
- [ ] **Subtitle Tab**
  - Generate subtitle với Whisper
  - Generate bilingual subtitle
  - Apply formatting
  - Manual merge mode
  
- [ ] **Dubbing Tab**
  - Generate TTS với Google TTS
  - Generate TTS với ElevenLabs
  - Apply BGM
  - Mux output
  
- [ ] **AI Editor Tab**
  - Gemini script editing (real API)
  - GPT script editing (real API)
  - Translation với OpenAI
  
- [ ] **YouTube Upload Tab**
  - Single upload với API
  - Batch upload
  - Thumbnail upload
  - Playlist management

**Success criteria:** ✅ Tất cả manual tests pass

### 4.2 UI/UX Validation
- [ ] Check: Theme switching works
- [ ] Check: All buttons responsive
- [ ] Check: Progress bars update
- [ ] Check: Error messages clear
- [ ] Check: Config saved/loaded correctly

---

## Phase 5: Performance Tests (Optional) ⚡

### 5.1 Basic Performance
- [ ] App startup time (< 5s)
- [ ] Service initialization time
- [ ] Large file processing
- [ ] Memory usage under load

### 5.2 Stress Tests
- [ ] Multiple concurrent downloads
- [ ] Large batch processing
- [ ] Extended session stability

---

## Test Execution Plan

### Week 1: Phases 1-2
- **Days 1-2:** Setup infrastructure + Basic service tests
- **Days 3-4:** Integration tests
- **Day 5:** Review và fix issues

### Week 2: Phases 3-4
- **Days 1-2:** Regression tests
- **Days 3-4:** Manual validation
- **Day 5:** Documentation

### Week 3: Optional Phase 5
- **Days 1-2:** Performance tests
- **Days 3-5:** Optimization nếu cần

---

## Bug Tracking

### Bug Severity Levels
- **P0 - Critical:** App crash, data loss → Fix ngay
- **P1 - High:** Main feature broken → Fix trong 24h
- **P2 - Medium:** Feature degraded → Fix trong 1 tuần
- **P3 - Low:** Minor issue → Fix trong 1 tháng

### Bug Template
```markdown
### [P1] Bug Title
**Services affected:** AI Service, Piu.py
**Steps to reproduce:**
1. ...
2. ...
3. ...
**Expected:** ...
**Actual:** ...
**Logs:**
```
[relevant log entries]
```
**Fix:** [Link to commit/PR]
```

---

## Success Metrics

### Must Have (Before release)
- ✅ All Phase 1 tests pass
- ✅ All Phase 2 tests pass
- ✅ Manual smoke tests pass
- ✅ No P0/P1 bugs

### Nice to Have
- ✅ Phase 3 tests pass
- ✅ Performance within targets
- ✅ Test coverage > 60%

### Documentation Deliverables
- [ ] Test execution report
- [ ] Bug report tổng hợp
- [ ] Performance metrics
- [ ] Known issues list

---

## Risk Mitigation

### Potential Issues
1. **Service mocking complex** → Start with real APIs for integration tests
2. **UI testing difficult** → Focus on logic, UI = manual
3. **Time constraints** → Prioritize critical path tests
4. **False positives** → Review failures carefully

### Contingency
- Nếu tests phát hiện nhiều bugs → Delay cleanup, focus fixes
- Nếu performance issues → Profile và optimize
- Nếu time overrun → Skip optional phases

---

## Next Steps After Testing

1. **If tests pass:** ✅ Proceed with documentation
2. **If critical bugs found:** 🔧 Fix bugs first
3. **If minor issues:** 📝 Document known issues
4. **Continuous:** Add tests as features evolve

---

**Estimated Total Time:** 8-12 giờ  
**Priority:** ⭐⭐⭐ High - Critical for stability  
**Status:** 🟢 Phase 1 Foundation - IN PROGRESS

**Phase 1 Progress:** ✅ **75% Complete**
- ✅ Test infrastructure setup
- ✅ Basic service initialization tests
- ✅ YouTube service comprehensive tests
- ✅ Metadata service comprehensive tests
- ✅ AI service basic tests
- ⏳ Model service tests (TODO)
- ⏳ Image service tests (TODO)

**Next Steps:**
1. Install pytest: `pip install pytest pytest-cov pytest-timeout pytest-mock`
2. Run existing tests: `pytest tests/integration/ -v`
3. Continue with more service tests
4. Proceed to Phase 2 integration tests

**Cập nhật lần cuối:** 2025-01-XX  
**Owner:** [TBD]

