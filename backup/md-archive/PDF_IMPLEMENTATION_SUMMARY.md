# PDF Domain Implementation Summary

**Status:** ✅ COMPLETE  
**Date:** Feb 15, 2026  
**Tests:** 17/17 PASSING  

## Implementation Overview

The PDF domain system has been fully integrated into the min-minisaas backend with modular, independent design following domain-driven design patterns. The system provides PDF file management, async conversion, and event-driven point deduction.

## Core Components

### 1. Domain Models (`app/domain/pdf/`)

#### PDFFile Model
- **Table:** `pdf_files`
- **Key Fields:**
  - `file_id` (UUID, unique) - Identifies file across system
  - `user_id` (UUID FK) - Multi-user isolation with CASCADE delete
  - `status` (VARCHAR) - FileStatus enum (uploading → uploaded → processing → processed/failed → deleted)
  - `minio_bucket`, `minio_path` - S3 object references
  - `file_size_bytes`, `page_count` - Metadata
  - `output_path`, `conversion_result` - Conversion data
  - `conversion_cost` - Points deducted (integer)
  - `is_deleted` - Soft delete flag
  - Timestamps: `created_at`, `updated_at`, `processed_at`

#### Enums
- `FileStatus` - uploading, uploaded, processing, processed, failed, deleted
- `FileType` - pdf, image, document (extensible)

### 2. Services

#### PDFConverterService (`pdf_converter_service.py`)
- `convert_pdf_to_csv()` - Uses pdfplumber with fallback text extraction
  - Returns: `{success, table_count, rows, error}`
- `extract_text()` - Extract all text from PDF
- `get_metadata()` - Page count, file size, title, author

#### PDFFileService (`pdf_file_service.py`)
- CRUD operations with event emission
- `create_pdf_file()` - Creates record, emits `PDFFileCreatedEvent`
- `get_pdf_file()` - By file_id
- `get_user_pdf_files()` - Paginated list (soft-delete filtered)
- `update_conversion_status()` - Track progress & point cost
- `soft_delete_pdf_file()` - Mark deleted, emits `PDFFileDeletedEvent`
- `get_total_conversion_cost()` - Sum user's point usage

### 3. API Endpoints

#### File Management Router (`endpoints/pdf/files.py`)

**POST /api/v1/pdf/upload**
```
Request: multipart/form-data with PDF file (100MB max)
Response: PDFFileResponse with file_id, status=UPLOADING → UPLOADED
Auth: Required (verify_any_platform)
Returns: 201 Created
```

**GET /api/v1/pdf/{file_id}**
```
Response: PDFFileResponse with full file metadata
Auth: Required + ownership check
Returns: 200 OK or 404/403
```

**GET /api/v1/pdf/user/files**
```
Query: skip (default 0), limit (1-100, default 20)
Response: List[PDFFileResponse]
Auth: Required
Returns: 200 OK with paginated list
```

**DELETE /api/v1/pdf/{file_id}**
```
Behavior: Soft delete (marks is_deleted, removes from MinIO)
Auth: Required + ownership check
Returns: 204 No Content
```

#### Conversion Router (`endpoints/pdf/convert.py`)

**POST /api/v1/pdf/{file_id}/convert**
```
Request: Optional PDFConversionRequest
Behavior: 
  1. Validates file status (must be UPLOADED)
  2. Adds background task immediately
  3. Returns 200 with status=PROCESSING
  4. Background task:
     - Downloads file from MinIO
     - Converts with PDFConverterService
     - Uploads result CSV to MinIO
     - Updates DB with conversion_cost
     - Emits PDFConversionCompletedEvent
Auth: Required + ownership check
Returns: 200 OK with conversion_cost=0 (charged on completion)
Status Codes: 404 (not found), 403 (access denied), 409 (already processing)
```

**GET /api/v1/pdf/{file_id}/status**
```
Response: PDFConversionResponse with status + human-readable message
Auth: Required + ownership check
Returns: 200 OK
Status Messages:
  - UPLOADING: "파일 업로드 중입니다."
  - UPLOADED: "파일이 준비되었습니다. 변환을 요청해주세요."
  - PROCESSING: "변환 중입니다. 잠시만 기다려주세요."
  - PROCESSED: "변환이 완료되었습니다."
  - FAILED: "변환에 실패했습니다."
```

### 4. Storage Integration (MinIO)

#### MinIOClient (`infrastructure/minio_client.py`)
- Wrapper around `minio.Minio` library
- Async-compatible methods:
  - `ensure_bucket()` - Create if not exists
  - `upload_file()` - With file size and content-type
  - `download_file()` - Returns BytesIO
  - `file_exists()` - Check existence
  - `delete_file()` - Remove object
  - `get_presigned_url()` - Temporary download link (future: output file delivery)

**Storage Structure:**
```
bucket: pdf-files
path: {user_id}/{file_id}/{original_filename}
output: {user_id}/{file_id}/output.csv
```

### 5. Event-Driven Architecture

#### Events (`app/core/events.py`)

1. **PDFFileCreatedEvent**
   - Payload: user_id, file_id, filename, file_size
   - Handler: Log creation (TODO: send notification)

2. **PDFFileStatusChangedEvent**
   - Payload: user_id, file_id, old_status, new_status
   - Handler: (Reserved for future audit logging)

3. **PDFConversionCompletedEvent**
   - Payload: user_id, file_id, output_path, conversion_cost
   - Handler: Deduct points (TODO: call Points Service)

4. **PDFFileDeletedEvent**
   - Payload: user_id, file_id
   - Handler: Log deletion (TODO: send notification)

#### Event Handlers (`services/pdf_event_handlers.py`)
- `PDFEventHandlers` class with static methods for each event
- Registered in `app/main.py` startup event
- `register_pdf_event_handlers()` called on app initialization

**Handler Implementation Status:**
- ✅ Logging complete for all events
- ⏳ Point deduction (TODO: integrate Points Service)
- ⏳ Notifications (TODO: integrate notification service)

### 6. Configuration

**MinIO Settings** (`app/core/config.py`):
```python
MINIO_ENDPOINT: str = "localhost:9000"
MINIO_ACCESS_KEY: str = "minioadmin"
MINIO_SECRET_KEY: str = "minioadmin"
MINIO_SECURE: bool = False
```

## Test Coverage

### Integration Tests (`tests/test_pdf_integration.py`) - 17 tests, ALL PASSING ✅

**TestPDFEndpointsExist (6 tests)**
- All 6 endpoints exist and don't return 404

**TestPDFAuthRequirements (6 tests)**
- Upload requires auth
- Get requires auth (ownership)
- List requires auth
- Delete requires auth (ownership)
- Convert requires auth (ownership)
- Status requires auth (ownership)

**TestPDFErrorHandling (4 tests)**
- Get nonexistent file → 404
- Delete nonexistent file → 404
- Convert nonexistent file → 404
- Status nonexistent file → 404

**TestPDFAPIStructure (1 test)**
- PDF routers properly integrated into main API

## Migration Chain

**Current Migration Chain:**
```
20260211_0001_baseline
    ↓
20260215_0002_board_system (Board models)
    ↓
20260215_0003_pdf_domain (PDF models) ← NEW
```

**PDF Migration Details:**
- Creates `pdf_files` table with 18 columns
- VARCHAR(20) columns for status with CHECK constraints
- 4 indexes for query performance (user_id, file_id, status, created_at)
- UUID foreign key to users with CASCADE delete

## Architecture Decisions

### Why This Design?

1. **Domain-Driven Design**
   - Isolated `app/domain/pdf/` structure prevents coupling
   - Can be extracted to separate service later
   - Clear separation of concerns (models, services, schemas)

2. **Event-Driven**
   - Async background processing via BackgroundTasks
   - Point deduction triggered by event emission
   - Decoupled from file management logic
   - Extensible for notifications, auditing, etc.

3. **MinIO S3 Storage**
   - User isolation: path structure groups by user_id
   - Scalable: files never on main server disk
   - Flexible: can change storage backend later
   - Temporary presigned URLs for secure downloads

4. **Soft Delete**
   - Files retained for audit/compliance
   - Excluded from user queries via `is_deleted` filter
   - Preserves foreign key relationships

5. **Async Conversion**
   - Immediate user feedback (200 response sent before processing)
   - Long-running conversion doesn't block request
   - Status endpoint for polling progress
   - Extensible for WebSocket updates later

## Remaining TODOs

### High Priority
- [ ] **Point Deduction:** Call Points Service in `handle_pdf_conversion_completed()`
  - Location: `app/domain/pdf/services/pdf_event_handlers.py:70`
  - Requires: Points Service interface definition

### Medium Priority
- [ ] **Notifications:** Send alerts for file creation, conversion completion
  - Location: `pdf_event_handlers.py` - handlers with TODO comments
  - Requires: Notification Service integration

### Low Priority (Infrastructure)
- [ ] **mTLS for Device/IoT:** Secure PDF device access
- [ ] **Hardware-based secrets:** TEE integration for sensitive operations

## Key Dependencies

```
FastAPI          - REST API framework
SQLAlchemy       - ORM with async support
pdfplumber       - PDF text/table extraction
minio            - S3-compatible storage client
PostgreSQL       - Primary database
Redis            - Event bus (via app/core/events.py)
```

## Performance Considerations

### Scalability
- **PDF Conversion:** Off-loaded to background task (non-blocking)
- **File List:** Paginated (limit 1-100, default 20)
- **Storage:** MinIO scales horizontally
- **Database:** Indexed on user_id, file_id, status for fast queries

### Optimization Opportunities (Future)
- [ ] Compression for stored CSVs
- [ ] Caching of conversion results
- [ ] Batch processing for multiple files
- [ ] Progressive upload for large PDFs

## Security

### Current Safeguards
✅ Authentication required on all endpoints (via `verify_any_platform`)
✅ Ownership checks on file operations (user_id matching)
✅ File type validation (PDF only on upload)
✅ File size limit (100MB)
✅ Soft delete preserves audit trail
✅ MinIO isolation per user_id

### Future Hardening
- [ ] Rate limiting on conversion requests
- [ ] Virus scanning on upload
- [ ] Encryption at rest for MinIO
- [ ] Audit logging for all file operations

## Files Summary

### Created (13)
```
app/domain/pdf/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── pdf_file.py                    (ORM model)
├── schemas/
│   └── pdf_file.py                    (Pydantic schemas)
└── services/
    ├── pdf_converter_service.py       (pdfplumber wrapper)
    ├── pdf_file_service.py            (CRUD operations)
    └── pdf_event_handlers.py          (Event processing)
app/api/v1/endpoints/pdf/
├── __init__.py
├── files.py                            (Upload, get, list, delete)
└── convert.py                          (Conversion, status)
app/infrastructure/
└── minio_client.py                    (S3 storage wrapper)
alembic/versions/
└── 20260215_0003_pdf_domain.py        (Migration)
tests/
└── test_pdf_integration.py            (17 tests)
```

### Modified (6)
```
app/core/events.py                      (+4 PDF events)
app/core/config.py                      (+MinIO config)
app/api/v1/__init__.py                  (+pdf_router)
app/main.py                             (+event handler registration)
app/db/model_registry.py                (+PDFFile)
app/domain/auth/models/__init__.py      (+exports)
```

## Deployment Checklist

- [x] Models created and migrated
- [x] API endpoints implemented
- [x] MinIO integration complete
- [x] Event handlers registered
- [x] 17/17 integration tests passing
- [x] Database connectivity verified
- [x] No breaking changes to existing code
- [ ] Points Service integrated
- [ ] Notification Service integrated
- [ ] Production MinIO credentials configured
- [ ] Rate limiting configured
- [ ] Monitoring/alerting setup

## API Documentation

For detailed API documentation with curl examples, see: `/Users/nenpa/Development/MyProjects/min-minisaas-backend/doc/PDF_API.md` (TODO: create if needed)

---

**Last Updated:** Feb 15, 2026  
**Next Review:** When Point Deduction integration is complete
