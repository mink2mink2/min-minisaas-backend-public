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
      POSTGRES_USER: minisaas
      POSTGRES_PASSWORD: localpassword
      POSTGRES_DB: minisaas_db
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
gcloud redis instances create minisaas-redis \
  --size=1 \
  --region=asia-northeast3 \
  --tier=basic \
  --redis-version=redis_7_0

# IP 주소 확인 (앱 환경변수에 사용)
gcloud redis instances describe minisaas-redis \
  --region=asia-northeast3 \
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
        - image: gcr.io/PROJECT/minisaas-backend:latest
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
export REGION=asia-northeast3
export SERVICE_NAME=minisaas-backend

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
gcloud sql instances create minisaas-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --availability-type=REGIONAL  # HA 구성

# 데이터베이스 생성
gcloud sql databases create minisaas --instance=minisaas-db

# 사용자 생성
gcloud sql users create minisaas \
  --instance=minisaas-db \
  --password=your-secure-password

# Cloud Run에 Cloud SQL 연결 설정
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:minisaas-db
```

---

## 7. 배포 후 검증

### 헬스체크

```bash
SERVICE_URL=$(gcloud run services describe minisaas-backend \
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
          docker build -t gcr.io/${{ vars.PROJECT_ID }}/minisaas-backend:${{ github.sha }} .
          docker push gcr.io/${{ vars.PROJECT_ID }}/minisaas-backend:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy minisaas-backend \
            --image=gcr.io/${{ vars.PROJECT_ID }}/minisaas-backend:${{ github.sha }} \
            --region=asia-northeast3
```

---

## 9. 트러블슈팅

### DB 연결 실패

```bash
# Cloud SQL Proxy로 로컬 연결 테스트
cloud-sql-proxy $PROJECT_ID:$REGION:minisaas-db --port=5432
psql -h localhost -U minisaas -d minisaas
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
