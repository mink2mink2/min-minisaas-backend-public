# PDF 기능 통합 + Flutter 코드 작성 - 구현 완료

구현일: 2026-03-04

## 📋 구현 현황

### Backend 변경사항 ✅ (4개 완료)

#### 1. `app/api/v1/endpoints/pdf/files.py` - 파일 상태 전환
**변경 내용:**
- 업로드 완료 후 파일 상태를 자동으로 UPLOADING → UPLOADED로 전환
- `update_conversion_status()` 호출 추가
- FileStatus import 추가

**코드 위치:** 라인 134-140

```python
await db.commit()

# 상태 전환: UPLOADING → UPLOADED
await pdf_service.update_conversion_status(
    file_id=pdf_file.file_id,
    status=FileStatus.UPLOADED,
)
await db.commit()
```

---

#### 2. `app/api/v1/endpoints/pdf/convert.py` - 포인트 잔액 확인

**변경 내용:**
- `request_pdf_conversion()` 함수에서 변환 요청 전 포인트 잔액 확인
- 포인트 부족 시 HTTP 402 (Payment Required) 응답

**코드 위치:** 라인 208-220

```python
# 포인트 잔액 확인
point_service = PointService(db)
balance = await point_service.get_balance(current_user.id)
if balance < CONVERSION_COST:
    raise HTTPException(
        status_code=402,
        detail=f"포인트가 부족합니다. 필요: {CONVERSION_COST}, 잔액: {balance}",
    )
```

---

#### 3. `app/api/v1/endpoints/pdf/convert.py` - 포인트 실제 차감

**변경 내용:**
- `convert_pdf_background()` 함수에서 변환 완료 후 실제 포인트 차감
- `PointService.consume()` 호출
- 멱등성 키로 중복 차감 방지: `f"pdf_convert_{file_id}"`
- 차감 실패 시 graceful handling (conversion_cost=0)

**코드 위치:** 라인 133-161

```python
# 포인트 차감 (변환 완료 후)
conversion_cost = CONVERSION_COST
try:
    point_service = PointService(db)
    await point_service.consume(
        user_id=pdf_file.user_id,
        amount=conversion_cost,
        description=f"PDF 변환: {pdf_file.original_filename}",
        idempotency_key=f"pdf_convert_{file_id}",
    )
except InsufficientPointsError:
    logger.error(f"❌ 포인트 부족으로 차감 실패: {file_id}")
    conversion_cost = 0
except Exception as e:
    logger.error(f"❌ 포인트 차감 중 오류: {e}")
    conversion_cost = 0
```

---

#### 4. `app/api/v1/endpoints/pdf/convert.py` - 다운로드 엔드포인트

**변경 내용:**
- 새로운 엔드포인트: `GET /api/v1/pdf/{file_id}/download`
- StreamingResponse로 MinIO에서 CSV 파일 스트리밍
- UTF-8 filename encoding 적용
- 파일 소유권 및 상태 검증

**코드 위치:** 라인 289-363

```python
@router.get("/{file_id}/download")
async def download_converted_csv(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """변환된 CSV 파일 다운로드 (스트리밍)"""
    # ... 구현 내용
```

**사용 예시:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  https://api.example.com/api/v1/pdf/abc123/download \
  -o result.csv
```

---

### Flutter 코드 ✅ (3개 파일 생성)

생성된 파일은 `flutter-pdf-code/` 디렉토리에 있습니다.

#### 1. `lib/domain/ai/models/pdf_models.dart`
**포함 클래스:**
- `PdfFile`: 파일 메타데이터 모델
  - fileId, originalFilename, fileSizeBytes, status
  - conversionCost, outputPath, createdAt, processedAt
  - fromJson/toJson 메서드 포함

- `PdfConversionStatus`: 변환 상태 모델
  - fileId, status, conversionCost, message
  - createdAt, processedAt
  - fromJson/toJson 메서드 포함

---

#### 2. `lib/domain/ai/services/pdf_service.dart`
**제공 메서드:**
- `uploadPdf(File)` → Future<PdfFile>
  - FormData를 사용한 파일 업로드

- `requestConversion(String fileId)` → Future<PdfConversionStatus>
  - 변환 요청 (402 에러 처리 포함)

- `getStatus(String fileId)` → Future<PdfConversionStatus>
  - 현재 변환 상태 조회

- `getUserFiles()` → Future<List<PdfFile>>
  - 사용자의 PDF 파일 목록 조회

- `getFileDetails(String fileId)` → Future<PdfFile>
  - 단일 파일 상세 정보 조회

- `downloadCsv(String fileId, String savePath)` → Future<void>
  - CSV 파일 다운로드

- `downloadCsvWithProgress()` → Future<void>
  - 진행률 콜백 포함 다운로드

- `deleteFile(String fileId)` → Future<void>
  - 파일 삭제

**예외 클래스:**
- `InsufficientPointsException`: 포인트 부족
- `PdfServiceException`: 일반 서비스 에러

---

#### 3. `lib/domain/ai/providers/pdf_providers.dart`
**제공 Provider들:**

1. **pdfServiceProvider**
   - PdfService 인스턴스 제공

2. **pdfFilesProvider** (StateNotifier)
   - 사용자 PDF 파일 목록 상태 관리
   - loadUserFiles(), uploadFile(), refreshFiles() 메서드

3. **pdfFileProvider** (FutureProvider)
   - 단일 파일 상세 정보 조회

4. **pdfConversionStatusProvider** (StateNotifier Family)
   - 변환 상태 추적
   - requestConversion(), checkStatus(), pollStatus() 메서드

5. **pdfConversionStatusFutureProvider**
   - 현재 변환 상태 조회

6. **conversionProgressProvider** (StateNotifier Family)
   - 변환 진행 상태 모니터링
   - 자동 폴링 로직 포함 (최대 10분, 2초 간격)

7. **pdfDownloadProvider** (FutureProvider)
   - 파일 다운로드 관리

---

## 🔌 Flutter 프로젝트에 추가하기

### 단계 1: 파일 복사
```bash
# flutter-pdf-code/ 디렉토리의 3개 파일을 복사합니다
cp flutter-pdf-code/*.dart <flutter-project>/lib/domain/ai/
```

### 단계 2: 디렉토리 구조
```
lib/domain/ai/
├── models/
│   └── pdf_models.dart
├── services/
│   └── pdf_service.dart
└── providers/
    └── pdf_providers.dart
```

### 단계 3: apiClientProvider 설정 필요
`pdf_providers.dart`에서 사용하는 `apiClientProvider`를 정의해야 합니다.

**예시:**
```dart
// lib/core/providers/api_providers.dart
final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: 'https://your-api.com',
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
  ));

  // Auth 인터셉터 추가
  // ... 구현

  return dio;
});
```

### 단계 4: 필수 의존성 확인
```yaml
dependencies:
  dio: ^5.0.0
  flutter_riverpod: ^2.0.0
  path_provider: ^2.0.0
```

---

## ✅ 검증 단계

### Backend 검증
```bash
# 1. 파일 업로드
POST /api/v1/pdf/upload
→ 응답에 "status": "uploaded" 확인

# 2. 포인트 부족 테스트 (포인트 0인 사용자로)
POST /api/v1/pdf/{file_id}/convert
→ HTTP 402 응답 + "포인트가 부족합니다" 메시지

# 3. 변환 상태 모니터링
GET /api/v1/pdf/{file_id}/status
→ status: "processing" → "processed" 진행 확인

# 4. 사용자 포인트 차감 확인
GET /api/v1/users/me
→ points: (이전값) - 10

# 5. 파일 다운로드
GET /api/v1/pdf/{file_id}/download
→ Content-Type: text/csv, CSV 파일 수신
```

### Flutter 검증
```dart
// 1. 파일 업로드
final pdfFile = await pdfService.uploadPdf(file);
assert(pdfFile.status == 'uploaded');

// 2. 변환 요청
try {
  await pdfService.requestConversion(fileId);
} on InsufficientPointsException catch (e) {
  print('포인트 부족: $e');
}

// 3. 상태 폴링
while (true) {
  final status = await pdfService.getStatus(fileId);
  if (status.status == 'processed') break;
  await Future.delayed(Duration(seconds: 2));
}

// 4. CSV 다운로드
final dir = await getApplicationDocumentsDirectory();
await pdfService.downloadCsv(fileId, '${dir.path}/result.csv');
```

---

## 🔐 보안 고려사항

1. **멱등성 키**: PDF 변환 포인트는 `idempotency_key=f"pdf_convert_{file_id}"`로 중복 차감 방지
2. **소유권 검증**: 모든 엔드포인트에서 `pdf_file.user_id == current_user.id` 확인
3. **상태 검증**: 다운로드는 `status == PROCESSED`일 때만 허용
4. **포인트 검증**: 변환 요청 전 잔액 확인 (402 응답)

---

## 📝 주의사항

- `convert_pdf_background()`는 BackgroundTask로 실행되므로 DB 세션이 요청 종료 후에도 유지됨
- 포인트 차감 실패해도 변환 결과는 유지되지만 `conversion_cost=0`으로 기록됨
- Flutter에서 폴링은 최대 10분, 2초 간격으로 설정됨 (필요시 조정)

---

## 📚 관련 파일

| 파일 | 역할 |
|------|------|
| `app/api/v1/endpoints/pdf/files.py` | 파일 업로드 + 상태 관리 |
| `app/api/v1/endpoints/pdf/convert.py` | 변환 + 다운로드 + 포인트 차감 |
| `app/domain/pdf/models/pdf_file.py` | PDFFile 데이터 모델 |
| `app/domain/pdf/services/pdf_file_service.py` | PDF 파일 서비스 |
| `app/domain/points/services/point_service.py` | 포인트 서비스 |
| `flutter-pdf-code/pdf_models.dart` | Flutter PDF 모델 |
| `flutter-pdf-code/pdf_service.dart` | Flutter PDF 서비스 |
| `flutter-pdf-code/pdf_providers.dart` | Flutter 상태 관리 |
