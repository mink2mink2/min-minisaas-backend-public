# min-minisaas Backend

FastAPI 기반 min-minisaas 백엔드 서버

## 🚀 빠른 시작

### 환경 설정
```bash
cp .env.example .env
# .env 파일에서 비밀번호 변경
```

### 실행
```bash
# Docker Compose 사용
docker-compose up -d

# 또는 로컬 실행
pip install -r api/requirements.txt
python api/app/main.py
```

## 📝 개발

### DB 자동화 (최초 설치/업데이트)
```bash
# 최초 1회: DB 생성 + 마이그레이션 + 런타임 검증
make setup

# 개별 실행
make bootstrap   # DB 없으면 생성
make migrate     # alembic upgrade head
make verify      # postgres/redis 연결 점검
```

### DB 문서
- Migration 운영 절차: `docs/DB_MIGRATION_WORKFLOW.md`
- 현재 스키마 개요: `docs/DB_SCHEMA_OVERVIEW.md`

### Code Style
- **Format**: Black
- **Import Sort**: isort
- **Lint**: flake8, pylint

### 자동 검사 (GitHub Actions)
커밋/PR 시 자동으로 format & lint 검사 실행

### 로컬 검사
```bash
# Format check
black --check api/
isort --check-only api/

# Lint
flake8 api/
pylint api/
```

## 📚 API 문서
http://localhost:8000/docs (Swagger UI)

## 🔗 관련 프로젝트
- [메인 저장소](https://github.com/your-username/min-minisaas)
- [Frontend](https://github.com/your-username/min-minisaas-web)
- [Mobile](https://github.com/your-username/min-minisaas-app)
