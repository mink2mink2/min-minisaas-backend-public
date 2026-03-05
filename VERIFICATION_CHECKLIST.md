# PDF 기능 통합 검증 체크리스트

작성일: 2026-03-04

## ✅ Backend 변경사항 확인

### 파일 1: `app/api/v1/endpoints/pdf/files.py`
- [x] FileStatus import 추가 (라인 11)
- [x] upload_pdf 함수에서 UPLOADING → UPLOADED 전환 추가 (라인 137-142)

**검증 명령:**
```bash
grep -n "FileStatus.UPLOADED" app/api/v1/endpoints/pdf/files.py
```

---

### 파일 2: `app/api/v1/endpoints/pdf/convert.py`

#### 2-1. Import 확인
- [x] PointService import (라인 15)
- [x] InsufficientPointsError import (라인 15)
- [x] StreamingResponse import (라인 7)
- [x] quote import (라인 5)

**검증 명령:**
```bash
grep -n "from app.domain.points.services" app/api/v1/endpoints/pdf/convert.py
grep -n "from urllib.parse import quote" app/api/v1/endpoints/pdf/convert.py
grep -n "StreamingResponse" app/api/v1/endpoints/pdf/convert.py
```

#### 2-2. 포인트 잔액 확인
- [x] CONVERSION_COST = 10 상수 (라인 25)
- [x] request_pdf_conversion()에 포인트 잔액 확인 코드 (라인 237-244)

**검증 명령:**
```bash
grep -n "CONVERSION_COST = 10" app/api/v1/endpoints/pdf/convert.py
grep -n "402" app/api/v1/endpoints/pdf/convert.py
```

#### 2-3. 포인트 실제 차감
- [x] convert_pdf_background()에서 PointService.consume() 호출 (라인 141-147)
- [x] 예외 처리 (라인 148-155)
- [x] idempotency_key 사용 (라인 146)

**검증 명령:**
```bash
grep -n "point_service.consume" app/api/v1/endpoints/pdf/convert.py
grep -n "idempotency_key" app/api/v1/endpoints/pdf/convert.py
```

#### 2-4. 다운로드 엔드포인트
- [x] @router.get("/{file_id}/download") 엔드포인트 추가 (라인 313)
- [x] StreamingResponse 반환 (라인 377)
- [x] 파일 소유권 검증 (라인 342)
- [x] 상태 검증 (라인 346)

**검증 명령:**
```bash
grep -n "download_converted_csv" app/api/v1/endpoints/pdf/convert.py
wc -l app/api/v1/endpoints/pdf/convert.py
```

---

## ✅ Flutter 파일 생성 확인

### 생성된 파일 목록

```bash
ls -lh flutter-pdf-code/
```

필요한 파일:
- [x] `flutter-pdf-code/pdf_models.dart` (3.0 KB)
- [x] `flutter-pdf-code/pdf_service.dart` (5.5 KB)
- [x] `flutter-pdf-code/pdf_providers.dart` (8.1 KB)

### 파일 내용 검증

**pdf_models.dart:**
- [x] PdfFile 클래스
- [x] PdfConversionStatus 클래스
- [x] fromJson() 메서드

**pdf_service.dart:**
- [x] uploadPdf() 메서드
- [x] requestConversion() 메서드
- [x] getStatus() 메서드
- [x] getUserFiles() 메서드
- [x] downloadCsv() 메서드
- [x] downloadCsvWithProgress() 메서드
- [x] deleteFile() 메서드
- [x] InsufficientPointsException 예외 클래스
- [x] PdfServiceException 예외 클래스

**pdf_providers.dart:**
- [x] pdfServiceProvider
- [x] pdfFilesProvider
- [x] pdfFileProvider
- [x] pdfConversionStatusProvider
- [x] conversionProgressProvider
- [x] pdfDownloadProvider

---

## 🧪 Backend 테스트 시나리오

### 테스트 1: 파일 업로드 후 상태 확인

```bash
# 1. PDF 파일 업로드
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.pdf" \
  https://api.example.com/api/v1/pdf/upload

# 예상 응답:
{
  "file_id": "abc-123",
  "original_filename": "test.pdf",
  "status": "uploaded",  # ← 이 값이 "uploaded"여야 함
  "file_size_bytes": 1024,
  "created_at": "2026-03-04T...",
  ...
}
```

### 테스트 2: 포인트 부족 시 402 응답

```bash
# 1. 포인트가 0인 사용자로 변환 요청
curl -X POST \
  -H "Authorization: Bearer USER_TOKEN_WITH_0_POINTS" \
  https://api.example.com/api/v1/pdf/abc-123/convert

# 예상 응답 (HTTP 402):
{
  "detail": "포인트가 부족합니다. 필요: 10, 잔액: 0"
}
```

### 테스트 3: 정상 변환 플로우

```bash
# 1. 충분한 포인트가 있는 사용자로 변환 요청
curl -X POST \
  -H "Authorization: Bearer USER_TOKEN_WITH_100_POINTS" \
  https://api.example.com/api/v1/pdf/abc-123/convert

# 예상 응답 (HTTP 202):
{
  "file_id": "abc-123",
  "status": "processing",
  "message": "변환이 시작되었습니다..."
}

# 2. 상태 확인 (폴링)
curl -X GET \
  -H "Authorization: Bearer TOKEN" \
  https://api.example.com/api/v1/pdf/abc-123/status

# 변환 중:
{
  "file_id": "abc-123",
  "status": "processing",
  "message": "변환 중입니다..."
}

# 변환 완료:
{
  "file_id": "abc-123",
  "status": "processed",
  "conversion_cost": 10,  # ← 포인트 10이 차감됨
  "output_path": "path/to/output.csv",
  "message": "변환이 완료되었습니다."
}
```

### 테스트 4: 파일 다운로드

```bash
# 1. CSV 파일 다운로드
curl -X GET \
  -H "Authorization: Bearer TOKEN" \
  https://api.example.com/api/v1/pdf/abc-123/download \
  -o result.csv

# 예상 응답:
# - HTTP 200
# - Content-Type: text/csv
# - Content-Disposition: attachment; filename*=UTF-8''test.csv
```

### 테스트 5: 포인트 차감 확인

```bash
# 변환 전 사용자 포인트 확인
curl -X GET \
  -H "Authorization: Bearer TOKEN" \
  https://api.example.com/api/v1/users/me

# Response: { "points": 100, ... }

# 변환 완료 후 사용자 포인트 확인
curl -X GET \
  -H "Authorization: Bearer TOKEN" \
  https://api.example.com/api/v1/users/me

# Response: { "points": 90, ... }  ← 10점 차감됨
```

---

## 🔐 보안 검증

### 소유권 검증
```bash
# 다른 사용자의 파일 다운로드 시도
curl -X GET \
  -H "Authorization: Bearer USER_2_TOKEN" \
  https://api.example.com/api/v1/pdf/USER_1_FILE_ID/download

# 예상 응답 (HTTP 403):
{
  "detail": "접근 권한이 없습니다."
}
```

### 상태 검증
```bash
# 아직 변환 중인 파일 다운로드 시도
curl -X GET \
  -H "Authorization: Bearer TOKEN" \
  https://api.example.com/api/v1/pdf/abc-123/download

# 예상 응답 (HTTP 409):
{
  "detail": "변환이 완료되지 않았습니다."
}
```

---

## 🐛 문제 해결

### Backend 테스트

**에러 1: "PointService not imported"**
- 확인: `app/api/v1/endpoints/pdf/convert.py` 라인 15에 import 있는지 확인

**에러 2: "FileStatus not imported" (files.py)**
- 확인: `app/api/v1/endpoints/pdf/files.py` 라인 11에 import 있는지 확인

**에러 3: "quote not imported"**
- 확인: `app/api/v1/endpoints/pdf/convert.py` 라인 5에서 urllib.parse import 확인

**에러 4: "StreamingResponse not imported"**
- 확인: `app/api/v1/endpoints/pdf/convert.py` 라인 7에 fastapi.responses import 확인

### Database 확인

```bash
# PDF 파일 생성 후 상태 확인 (DB)
sqlite3 database.db "SELECT file_id, status FROM pdf_files ORDER BY created_at DESC LIMIT 1;"

# 예상 결과:
# file_id | status
# abc-123 | uploaded
```

---

## 📝 요약

모든 구현이 완료되었습니다. 다음 단계:

1. **Backend 테스트**: 위 테스트 시나리오 실행
2. **Flutter 통합**: `flutter-pdf-code/` 파일들을 Flutter 프로젝트에 복사
3. **E2E 테스트**: 전체 플로우 (업로드 → 변환 → 다운로드) 검증

---

## 📦 파일 크기 및 라인 수

```
Backend:
  app/api/v1/endpoints/pdf/files.py  ← +12 라인 (상태 전환 추가)
  app/api/v1/endpoints/pdf/convert.py ← +85 라인 (포인트 + 다운로드)

Flutter:
  flutter-pdf-code/pdf_models.dart      (100줄)
  flutter-pdf-code/pdf_service.dart     (177줄)
  flutter-pdf-code/pdf_providers.dart   (248줄)
```

---

**상태**: ✅ 구현 완료
**검증**: 준비 완료
**배포**: 테스트 후 진행 가능
