# I/30 — 배포 가이드 (Deployment Guide)

> 최종 갱신: 2026-03-03
> 대상 환경: GCP (Cloud Run + Cloud SQL + Memorystore)

---

## 사전 요구사항

- GCP 프로젝트 생성 및 결제 계정 연결
- `gcloud` CLI 설치 및 인증 (`gcloud auth login`)
- Docker 설치
- Firebase 프로젝트 생성 및 서비스 계정 키 발급

---

## 1. 환경변수 설정

### 필수 환경변수

```bash
# .env 파일 또는 GCP Secret Manager에 등록

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:password@/dbname?host=/cloudsql/project:region:instance

# Redis
REDIS_URL=redis://10.0.0.x:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Firebase (FCM + Google Auth)
FIREBASE_CREDENTIALS_PATH=/secrets/firebase-credentials.json
# 또는 JSON 내용을 직접 환경변수로
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# Kakao OAuth
KAKAO_REST_API_KEY=your_kakao_rest_api_key

# Naver OAuth
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# 앱 설정
PRODUCTION=true
ALLOWED_ORIGINS=https://your-app.com,https://your-admin.com
```

### 환경변수 검증 스크립트

```bash
# 필수 환경변수가 모두 설정되었는지 확인
python -c "
from app.core.config import settings
print('DATABASE_URL:', bool(settings.DATABASE_URL))
print('JWT_SECRET_KEY:', bool(settings.JWT_SECRET_KEY))
print('FIREBASE_CREDENTIALS_PATH:', bool(settings.FIREBASE_CREDENTIALS_PATH))
print('KAKAO_REST_API_KEY:', bool(settings.KAKAO_REST_API_KEY))
print('NAVER_CLIENT_ID:', bool(settings.NAVER_CLIENT_ID))
print('All OK' if all([...]) else 'MISSING REQUIRED VARS')
"
```

---

## 2. Docker 설정

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 포트 노출
EXPOSE 8080

# 실행 (uvicorn workers: CPU 코어 수 기반)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

### docker-compose.yml (로컬 개발)

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8080"
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./secrets:/secrets:ro  # Firebase 키 마운트

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: your-service
      POSTGRES_PASSWORD: localpassword
      POSTGRES_DB: your-database-name
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 로컬 실행

```bash
# Docker Compose로 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 로컬 API 테스트
curl http://localhost:8000/health
```

---

## 3. 데이터베이스 마이그레이션

### 초기 마이그레이션 (최초 배포)

```bash
# 컨테이너 내부 또는 로컬에서 실행
export DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

# 마이그레이션 상태 확인
alembic current

# 최신 버전으로 마이그레이션 실행
alembic upgrade head

# 마이그레이션 이력 확인
alembic history --verbose
```

### Production 마이그레이션 절차

```bash
# 1. Staging에서 먼저 테스트
export DATABASE_URL=$STAGING_DATABASE_URL
alembic upgrade head
python -m pytest tests/ -x -q  # 테스트 통과 확인

# 2. Production 마이그레이션 (서비스 중단 없이)
export DATABASE_URL=$PRODUCTION_DATABASE_URL
alembic upgrade head

# 3. 롤백이 필요한 경우
alembic downgrade -1  # 한 단계 롤백
```

### 새 마이그레이션 생성

```bash
# 모델 변경 후 마이그레이션 자동 생성
alembic revision --autogenerate -m "add_user_nickname_column"

# 생성된 파일 검토 후 커밋
cat migrations/versions/xxxx_add_user_nickname_column.py
```

---

## 4. Redis 설정

### 로컬 Redis

```bash
# Docker로 Redis 실행
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 연결 테스트
redis-cli ping  # PONG 확인
```

### GCP Memorystore 설정

```bash
# Memorystore for Redis 인스턴스 생성
gcloud redis instances create your-redis-instance \
  --size=1 \
  --region=your-gcp-region \
  --tier=basic \
  --redis-version=redis_7_0

# IP 주소 확인 (앱 환경변수에 사용)
gcloud redis instances describe your-redis-instance \
  --region=your-gcp-region \
  --format="value(host)"
```

---

## 5. Firebase 설정

### 서비스 계정 키 발급

1. [Firebase 콘솔](https://console.firebase.google.com) → 프로젝트 설정
2. 서비스 계정 → 새 비공개 키 생성
3. JSON 파일 다운로드 (절대 Git에 커밋하지 않음)

### GCP Secret Manager에 등록

```bash
# Firebase 서비스 계정 키를 Secret Manager에 등록
gcloud secrets create firebase-credentials \
  --data-file=./firebase-credentials.json

# Cloud Run 서비스에 Secret 접근 권한 부여
gcloud secrets add-iam-policy-binding firebase-credentials \
  --member="serviceAccount:your-service-account@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Cloud Run에서 Secret 마운트

```yaml
# cloud-run-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      containers:
        - image: gcr.io/PROJECT/your-service-name:latest
          volumeMounts:
            - name: firebase-credentials
              mountPath: /secrets
              readOnly: true
      volumes:
        - name: firebase-credentials
          secret:
            secretName: firebase-credentials
```

---

## 6. GCP Cloud Run 배포

### Docker 이미지 빌드 및 푸시

```bash
# 프로젝트 변수 설정
export PROJECT_ID=your-gcp-project-id
export REGION=your-gcp-region
export SERVICE_NAME=your-service-name

# Docker 이미지 빌드
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

# GCP Container Registry에 푸시
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest
```

### Cloud Run 배포

```bash
# Cloud Run 서비스 배포
gcloud run deploy $SERVICE_NAME \
  --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=2 \
  --max-instances=20 \
  --memory=512Mi \
  --cpu=1 \
  --port=8080 \
  --set-env-vars="PRODUCTION=true" \
  --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET_KEY=jwt-secret:latest" \
  --add-volume=name=firebase-credentials,type=secret,secret=firebase-credentials \
  --add-volume-mount=volume=firebase-credentials,mount-path=/secrets

# 배포 상태 확인
gcloud run services describe $SERVICE_NAME --region=$REGION

# 서비스 URL 확인
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.url)"
```

### Cloud SQL 연결 설정

```bash
# Cloud SQL 인스턴스 생성 (PostgreSQL 15)
gcloud sql instances create your-cloudsql-instance \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --availability-type=REGIONAL  # HA 구성

# 데이터베이스 생성
gcloud sql databases create your-service --instance=your-cloudsql-instance

# 사용자 생성
gcloud sql users create your-service \
  --instance=your-cloudsql-instance \
  --password=your-secure-password

# Cloud Run에 Cloud SQL 연결 설정
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:your-cloudsql-instance
```

---

## 7. 배포 후 검증

### 헬스체크

```bash
SERVICE_URL=$(gcloud run services describe your-service-name \
  --region=$REGION \
  --format="value(status.url)")

# 헬스체크
curl $SERVICE_URL/health
# 기대 응답: {"status":"healthy","database":"connected","redis":"connected"}

# Auth API 테스트 (Google ID Token 필요)
curl -X POST $SERVICE_URL/api/v1/auth/login/google \
  -H "Content-Type: application/json" \
  -d '{"id_token":"your_firebase_id_token"}'
```

### 마이그레이션 확인

```bash
# Cloud Run Job으로 마이그레이션 실행
gcloud run jobs create migrate \
  --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region=$REGION \
  --command="alembic" \
  --args="upgrade,head" \
  --set-env-vars="DATABASE_URL=..." \
  --max-retries=1

gcloud run jobs execute migrate --region=$REGION --wait
```

---

## 8. CI/CD 설정 (선택사항)

### GitHub Actions 워크플로우

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/ -x -q

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS }}

      - name: Build and push Docker image
        run: |
          docker build -t gcr.io/${{ vars.PROJECT_ID }}/your-service-name:${{ github.sha }} .
          docker push gcr.io/${{ vars.PROJECT_ID }}/your-service-name:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy your-service-name \
            --image=gcr.io/${{ vars.PROJECT_ID }}/your-service-name:${{ github.sha }} \
            --region=your-gcp-region
```

---

## 9. 트러블슈팅

### DB 연결 실패

```bash
# Cloud SQL Proxy로 로컬 연결 테스트
cloud-sql-proxy $PROJECT_ID:$REGION:your-cloudsql-instance --port=5432
psql -h localhost -U your-service -d your-service
```

### FCM 발송 실패

```bash
# Firebase 서비스 계정 키 확인
python -c "
import firebase_admin
from firebase_admin import credentials
cred = credentials.Certificate('/secrets/firebase-credentials.json')
app = firebase_admin.initialize_app(cred)
print('Firebase OK')
"
```

### Redis 연결 실패

```bash
# VPC 네트워크에서 Memorystore 접근 테스트
gcloud run jobs create redis-test \
  --image=redis:7-alpine \
  --region=$REGION \
  --command="redis-cli" \
  --args="-h,REDIS_HOST,-p,6379,ping" \
  --vpc-connector=your-vpc-connector
```

---

## DB Migration Workflow

## 목적
이 문서는 `your-service-name`의 데이터베이스 변경을 안전하게 배포하기 위한 표준 절차를 정의합니다.

## 원칙
- 스키마 변경은 반드시 Alembic migration으로 관리합니다.
- 운영 경로에서 `Base.metadata.create_all()`을 직접 호출하지 않습니다.
- 최초 설치와 업데이트를 분리합니다.
  - 최초 설치: `bootstrap + migrate + seed-categories + verify`
  - 업데이트: `migrate + seed-categories + seed-blog-categories + verify`
- `verify`는 연결성뿐 아니라 필수 테이블/컬럼 스키마 가드와 기본 카테고리 seed 가드까지 통과해야 성공으로 봅니다.

## 명령 요약
```bash
# 최초 설치
make setup

# 개별 실행
make bootstrap   # DB 없으면 생성
make migrate     # alembic upgrade head
make seed-categories  # board 기본 카테고리 멱등 시드
make seed-blog-categories  # blog 기본 카테고리 멱등 시드
make verify      # postgres/redis + 필수 스키마 점검
make verify-schema  # 필수 스키마 점검 단독 실행
make release-prepare  # 운영 업데이트용(bootstrap 없이 migrate+seed+verify)
```

## 신규 스키마 변경 절차
1. SQLAlchemy 모델 수정
2. 마이그레이션 생성
```bash
.venv/bin/alembic revision --autogenerate -m "describe change"
```
3. 생성된 revision 검토 (nullable/default/index/drop 안전성 확인)
4. 로컬 적용
```bash
make migrate
```
5. 런타임 검증
```bash
make verify
.venv/bin/pytest -q tests/test_runtime_connectivity.py
```
6. 필요 시 downgrade 검증
```bash
.venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head
```

## 배포 순서
1. 앱 배포 전 DB migration 먼저 적용 (`make migrate`)
2. migration 성공 후 seed 적용 (`make seed-categories && make seed-blog-categories`)
3. `make verify` 통과 확인
4. 검증 통과 후 앱 버전 배포

## 롤백 원칙
- 긴급 이슈 시 앱 기능 플래그로 우선 차단
- DB 롤백이 필요한 경우에만 `alembic downgrade` 수행
- 파괴적 변경(drop/rename)은 expand-contract 전략으로 2회 배포로 처리

## Expand-Contract 규칙
- Expand: 컬럼/테이블 추가, 구버전과 호환
- Migrate: 앱이 신구 스키마 모두 읽고 쓰도록 과도기 운영
- Contract: 구 컬럼 제거

## 운영 체크리스트
- `.env`의 `DATABASE_URL`, `REDIS_URL`, `REDIS_PASSWORD` 확인
- migration 파일 리뷰 완료
- 백업/스냅샷 전략 확인
- 배포 후 `tests/test_runtime_connectivity.py` 통과 확인

## Fail to Success 운영 규칙
- `make verify` 또는 `make verify-schema`가 실패하면 앱 배포/재시작을 진행하지 않습니다.
- 담당자는 실패 메시지의 테이블/컬럼 누락 원인에 맞는 migration을 적용합니다.
  - 기본 조치: `.venv/bin/alembic upgrade head`
  - migration 누락이면 새 revision 추가 후 재적용
- seed 누락 실패 시 기본 조치:
  - `.venv/bin/python scripts/seed_board_categories.py`
  - `.venv/bin/python scripts/seed_blog_categories.py`
- 조치 후 `make verify`를 재실행해 success를 확인한 뒤에만 서비스 오픈합니다.

---

# Backend CI/CD & Cloud Run Deployment Guide

**Last Updated:** Feb 17, 2026
**Status:** Ready for GCP Setup
**Target Environment:** Google Cloud Run (your-gcp-region / Japan)

---

## 📋 Overview

This guide covers:
1. Docker containerization (Dockerfile)
2. GitHub Actions CI/CD pipeline
3. Google Cloud Run deployment
4. VPC Network + Serverless VPC Connector integration
5. Custom domain setup via Cloudflare

---

## 🚀 Deployment Architecture

```
GitHub (Source)
    ↓
GitHub Actions (CI/CD Pipeline)
    ↓
Docker Build → Artifact Registry (your-gcp-region)
    ↓
Cloud Run Service (your-gcp-region)
    ↓
VPC Connector → VPC Network → Cloud SQL (Fixed IP)
    ↓
Cloudflare DNS (api.yourdomain.com) → Cloud Run Service
```

---

## 📦 What's Already Done

### ✅ Dockerfile
- **Location:** `/Dockerfile`
- **Features:**
  - Multi-stage build (builder + runtime)
  - Python 3.11 slim base image
  - Port 8080 exposed (Cloud Run default)
  - Health check endpoint configured
  - Uvicorn command ready

### ✅ GitHub Actions Workflow
- **Location:** `.github/workflows/deploy.yml`
- **Triggers:** Push to `main` branch or manual workflow dispatch
- **Steps:**
  1. Checkout code
  2. Setup Google Cloud SDK
  3. Configure Docker auth for Artifact Registry
  4. Build & push Docker image
  5. Deploy to Cloud Run with VPC Connector
  6. Output service URL

### ✅ Environment Configuration
- **.env.production:** User must create (will be mapped to Cloud Run env vars)
- **Port:** 8080 (hardcoded in Dockerfile and Cloud Run)
- **Region:** your-gcp-region (hardcoded in workflow)

---

## 🔧 GitHub Secrets Setup

You must set these 3 secrets in your GitHub repository:

### 1. GCP_PROJECT_ID
- **Value:** Your GCP project ID (e.g., `your-gcp-project-id`)
- **Where to find:**
  - Go to Google Cloud Console
  - Click project selector (top-left)
  - Copy the Project ID field

### 2. GCP_SA_KEY
- **Value:** Full JSON content of Service Account key
- **Steps to create:**
  1. Google Cloud Console → IAM and Admin → Service Accounts
  2. Create new service account (name: `your-service-account-name`)
  3. Grant these roles:
     - `Cloud Run Developer`
     - `Artifact Registry Writer`
     - `Compute Network User` (for VPC Connector)
  4. Create JSON key
  5. Copy entire JSON content to GitHub Secret

### 3. VPC_CONNECTOR_NAME
- **Value:** Name of your Serverless VPC Connector (e.g., `your-gcp-region-vpc-connector`)
- **Where to find:**
  - Google Cloud Console → VPC Network → Serverless VPC Connectors
  - Copy the connector name for your-gcp-region

---

## 📋 Pre-Deployment Checklist

Before running the CI/CD pipeline, ensure these GCP resources exist:

### Required GCP Resources

- [ ] **GCP Project Created**
  - Project ID: ___________________

- [ ] **VPC Network**
  - Name: ___________________
  - CIDR Range: ___________________

- [ ] **Cloud Router**
  - Name: ___________________
  - Network: ___________________

- [ ] **Cloud NAT**
  - Configured on Cloud Router
  - Reserve static IP for outbound traffic
  - Static IP address: ___________________

- [ ] **Serverless VPC Connector**
  - Name: ___________________
  - Region: `your-gcp-region`
  - Network: [your VPC name]
  - IP range: ___________________

- [ ] **Artifact Registry Repository**
  - Repository name: `your-service-name`
  - Region: `your-gcp-region`
  - Format: `Docker`

- [ ] **Cloud SQL (Database)**
  - Instance name: ___________________
  - VPC Network: [your VPC name]
  - Private IP: ___________________
  - Public IP: NONE (private connectivity only)

- [ ] **Service Account**
  - Name: `your-service-account-name`
  - Has roles:
    - [ ] Cloud Run Developer
    - [ ] Artifact Registry Writer
    - [ ] Compute Network User
  - JSON key created: [ ]

---

## 🔐 GitHub Secrets Configuration

### Step 1: Navigate to Repository Settings
```
GitHub → Repository → Settings → Secrets and variables → Actions
```

### Step 2: Add Three Secrets

#### Secret #1: GCP_PROJECT_ID
- **Name:** `GCP_PROJECT_ID`
- **Value:** (Your GCP project ID)

#### Secret #2: GCP_SA_KEY
- **Name:** `GCP_SA_KEY`
- **Value:** (Full JSON key content)
- **Example format:**
  ```json
  {
    "type": "service_account",
    "project_id": "your-gcp-project-id",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "your-service-account@your-gcp-project-id.iam.gserviceaccount.com",
    ...
  }
  ```

#### Secret #3: VPC_CONNECTOR_NAME
- **Name:** `VPC_CONNECTOR_NAME`
- **Value:** (Your VPC Connector name, e.g., `your-gcp-region-vpc-connector`)

### Step 3: Verify All Secrets Added
```
Settings → Secrets and variables → Actions
Should show 3 secrets:
✅ GCP_PROJECT_ID
✅ GCP_SA_KEY
✅ VPC_CONNECTOR_NAME
```

---

## 📝 Environment Configuration (.env.production)

Create `.env.production` file in the backend root directory with production values:

```bash
# Example structure (user to fill in actual values)
ENVIRONMENT=production
DEBUG=False

# Database
DATABASE_URL=postgresql+asyncpg://user:password@[PRIVATE_IP]:5432/your-database-name

# Redis
REDIS_URL=redis://[REDIS_HOST]:6379/0

# Security
COOKIE_SECURE=True
COOKIE_SAMESITE=Lax
SECRET_KEY=[YOUR_SECRET_KEY]
API_SECRET_KEY=[YOUR_API_KEY]

# Firebase
FCM_CREDENTIALS_PATH=/path/to/firebase-key.json

# MinIO
MINIO_ENDPOINT=minio.example.com
MINIO_ACCESS_KEY=[YOUR_KEY]
MINIO_SECRET_KEY=[YOUR_SECRET]
MINIO_SECURE=True

# Stripe
STRIPE_SECRET_KEY=[YOUR_STRIPE_KEY]

# Slack (optional)
SLACK_WEBHOOK_URL=[YOUR_SLACK_WEBHOOK]
```

**⚠️ Important:**
- Do NOT commit `.env.production` to git
- GitHub Actions will map these to Cloud Run environment variables
- Sensitive values should be managed via GitHub Secrets if possible

---

## 🚀 Deployment Process

### First-Time Deployment

1. **Ensure GitHub Secrets are set**
   ```bash
   GCP_PROJECT_ID=✓
   GCP_SA_KEY=✓
   VPC_CONNECTOR_NAME=✓
   ```

2. **Ensure .env.production exists locally**
   ```bash
   cp .env.example .env.production
   # Edit .env.production with production values
   ```

3. **Push to main branch**
   ```bash
   git add .
   git commit -m "Deploy: Initial Cloud Run setup"
   git push origin main
   ```

4. **Monitor GitHub Actions**
   ```
   GitHub → Actions → Deploy to Cloud Run
   Watch the workflow execute
   ```

5. **Verify deployment**
   ```bash
   # Get Cloud Run service URL
   gcloud run services describe your-service-name \
     --region your-gcp-region \
     --format 'value(status.url)'

   # Test health endpoint
   curl https://[SERVICE_URL]/health
   ```

### Subsequent Deployments

Just push to `main` branch:
```bash
git push origin main
# GitHub Actions automatically triggers deployment
```

---

## 🌐 Cloudflare Domain Setup

### Connect api.yourdomain.com to Cloud Run

1. **Get Cloud Run service URL**
   ```bash
   gcloud run services describe your-service-name \
     --region your-gcp-region \
     --format 'value(status.url)'
   # Returns: https://your-service-name-[hash].a.run.app
   ```

2. **In Cloudflare Dashboard**
   - DNS → Add Record
   - Type: `CNAME`
   - Name: `api`
   - Content: `your-service-name-[hash].a.run.app`
   - Proxy status: `Proxied` (Orange cloud)
   - TTL: Auto

3. **Enable HTTPS**
   - Cloudflare automatically provisions SSL/TLS
   - Cloud Run provides HTTPS by default
   - Combined = Full HTTPS chain

4. **Test custom domain**
   ```bash
   curl https://api.yourdomain.com/health
   # Should return: {"status": "ok"}
   ```

---

## 📊 Cloud Run Configuration Details

### Service Settings (Automated by GitHub Actions)

- **Service Name:** `your-service-name`
- **Region:** `your-gcp-region` (Tokyo)
- **Platform:** Managed
- **Allow Unauthenticated:** Yes (API is public)
- **VPC Connector:** [VPC_CONNECTOR_NAME]
- **Egress:** All traffic (VPC + Internet)
- **Memory:** 512 MB
- **CPU:** 1 vCPU
- **Timeout:** 3600s (1 hour)
- **Max Instances:** 100
- **Port:** 8080

### Environment Variables (Mapped from .env.production)

All variables in `.env.production` are automatically mapped to Cloud Run environment variables by the GitHub Actions workflow.

```yaml
# From workflow: .github/workflows/deploy.yml
--set-env-vars="$(cat .env.production | tr '\n' ',')"
```

---

## 🔍 Monitoring & Logs

### View Cloud Run Logs

```bash
# All logs
gcloud run services logs read your-service-name \
  --region your-gcp-region \
  --limit 50

# Filter errors
gcloud run services logs read your-service-name \
  --region your-gcp-region \
  --limit 50 | grep -i error

# Real-time logs
gcloud run services logs read your-service-name \
  --region your-gcp-region \
  --follow
```

### Cloud Logging Dashboard

- Google Cloud Console → Cloud Logging
- Filter by service: `resource.service.name="your-service-name"`
- View structured logs, errors, performance metrics

---

## 🛠️ Troubleshooting

### 403 Forbidden on Artifact Registry

**Cause:** Service Account lacks `Artifact Registry Writer` role

**Fix:**
```bash
gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member=serviceAccount:your-service-account-name@[PROJECT_ID].iam.gserviceaccount.com \
  --role=roles/artifactregistry.writer
```

### VPC Connector Connection Failed

**Cause:** VPC Connector name incorrect or VPC network mismatch

**Fix:**
1. Verify VPC Connector exists in your-gcp-region
2. Ensure Service Account has `Compute Network User` role
3. Verify VPC Connector points to correct VPC

### Database Connection Timeout

**Cause:** Cloud SQL not in VPC or firewall blocking

**Fix:**
1. Ensure Cloud SQL has Private IP in same VPC
2. Check firewall rules allow port 5432
3. Verify connection string uses Private IP (not public)

### Environment Variables Not Set

**Cause:** .env.production file doesn't exist or workflow syntax error

**Fix:**
1. Create `.env.production` with all required variables
2. Verify GitHub Actions log for parsing errors
3. Check Cloud Run environment variables in console

---

## 📝 Workflow File Reference

**Location:** `.github/workflows/deploy.yml`

**Key Environment Variables:**
- `GCP_PROJECT_ID` → From GitHub Secret
- `GCP_REGION` → Hardcoded: `your-gcp-region`
- `SERVICE_NAME` → Hardcoded: `your-service-name`
- `REGISTRY_HOSTNAME` → Hardcoded: `your-gcp-region-docker.pkg.dev`

**Key Secrets Used:**
- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `VPC_CONNECTOR_NAME`

---

## ✅ Deployment Checklist

Before first deployment:

- [ ] GCP Project created
- [ ] VPC Network + Cloud Router + Cloud NAT configured
- [ ] Serverless VPC Connector created in your-gcp-region
- [ ] Artifact Registry repository created
- [ ] Cloud SQL configured with Private IP in same VPC
- [ ] Service Account created with proper roles
- [ ] Service Account JSON key ready
- [ ] GitHub Secrets configured (3 secrets)
- [ ] `.env.production` created with all values
- [ ] Dockerfile exists
- [ ] GitHub Actions workflow exists
- [ ] Custom domain ready (api.yourdomain.com in Cloudflare)

---

## 🚀 Deployment Command Reference

```bash
# Trigger deployment manually (if needed)
gh workflow run deploy.yml --ref main

# View deployment status
gh run list --workflow deploy.yml --limit 5

# View latest deployment logs
gh run view $(gh run list --workflow deploy.yml --limit 1 --json databaseId -q '.[0].databaseId')

# Get Cloud Run service URL
gcloud run services describe your-service-name \
  --region your-gcp-region \
  --format 'value(status.url)'

# Test service health
curl https://api.yourdomain.com/health
```

---

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Serverless VPC Connector Guide](https://cloud.google.com/vpc/docs/serverless-vpc-access)
- [GitHub Actions Google Cloud Setup](https://github.com/google-github-actions/setup-gcloud)
- [FastAPI on Cloud Run](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/python)
- [Cloudflare DNS Management](https://developers.cloudflare.com/dns/)

---

**Document Status:** ✅ Ready for Implementation
**Last Updated:** Feb 17, 2026
**Next Step:** Provide GCP project details to proceed with Secrets setup
