**[English](#english) | [한국어](#korean)**

---

<a name="english"></a>

# 🏗️ min-minisaas-backend — SaaS Backend API

> FastAPI-based backend server powering the MinFox app. Currently deployed on GCP Cloud Run for testing and development.

## 🚧 Project Status

**Work in Progress** — This project is under active development and is not yet a finished product.

The backend powers **MinFox (민폭스)**, a SaaS app currently available as a public test on the App Store.

## 🤖 Development Process

This project was conceptually designed and directed by me.
Most of the implementation code was generated with the assistance of AI tools.

My role focuses on reviewing the generated code, identifying issues that AI cannot resolve, fixing bugs, and validating the overall functionality.

Development continues while the app is being tested in a real environment.

---

## Overview

A FastAPI backend designed for a multi-tenant SaaS mobile app. Features OAuth social login, real-time WebSocket chat, community board, blog, push notifications, and a points system — all built on DDD + Event-driven architecture.

> This repository focuses on backend architecture and API development for the MinFox mobile application ecosystem.

### Key Features

- **Auth**: Google / Kakao / Naver OAuth + JWT (Web / Mobile / Desktop / IoT strategies)
- **Chat**: Real-time 1:1 chat via WebSocket
- **Board**: Community posts, comments, likes, bookmarks, search
- **Blog**: Posts, subscriptions, feed, likes
- **Push**: FCM token management + notification dispatch
- **Points**: Points charge / consume / refund
- **Architecture**: DDD + Event-driven (EventBus), extensive REST API endpoints
- **Security**: Rate limiting, CORS, HTTPS-only cookie auth
- **CI/CD**: GitHub Actions → GCP Artifact Registry → Cloud Run

---

## ⚠️ Note for Public Repository

This repository is a public-safe version of the project.

Sensitive configuration files, credentials, and deployment settings have been removed for security reasons.
Because of this, the project may not run immediately after cloning.

To run the project locally, additional configuration (environment variables, service credentials, and infrastructure setup) is required.
Configuration examples are provided via `.env.example`.

The code is provided mainly for architecture reference and development context.

---

## Quick Start

> Example development setup — requires your own `.env` configuration and running infrastructure (PostgreSQL, Redis, Firebase).

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 2. Run with Docker Compose
docker-compose up -d

# 3. Or run locally
pip install -r api/requirements.txt
python api/app/main.py
```

**API Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Database Setup

```bash
# First-time setup: create DB + migrate + seed + verify
make setup

# Individual commands
make bootstrap        # Create DB if not exists
make migrate          # alembic upgrade head
make seed-categories  # Seed default board categories
make verify           # Check postgres/redis + schema (fails deployment if broken)

# Pre-deploy (without bootstrap)
make release-prepare  # migrate + seed + verify
```

---

## Event-Driven Architecture

All domain state changes are published as events. Subscribers handle business logic, keeping domains loosely coupled.

**Implementation status (2026-03-04):**
- ✅ Board: posts, comments, likes
- ✅ Chat: rooms, messages
- ✅ Points: charge, consume, refund
- ✅ PDF: file operations
- 🟡 Blog: partial (create only)
- ❌ User profile updates (not yet)

---

## Tech Stack

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=flat&logo=firebase&logoColor=black)
![GCP](https://img.shields.io/badge/GCP_Cloud_Run-4285F4?style=flat&logo=googlecloud&logoColor=white)

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11+ |
| **Framework** | FastAPI 0.100+ |
| **Database** | PostgreSQL 15+ |
| **Cache / EventBus** | Redis 7+ |
| **Auth** | Firebase Admin SDK, JWT, OAuth 2.0 |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Deploy** | GCP Cloud Run |
| **CI/CD** | GitHub Actions |

---

## Code Style

- **Format**: Black
- **Import Sort**: isort
- **Lint**: flake8, pylint
- Auto-checked on every commit/PR via GitHub Actions

---

---

## 📱 MinFox App (Public Test)

This project is part of the **MinFox ecosystem**.

The mobile application that integrates features from this repository is currently available as a **public test on the App Store**, actively being tested while development continues.

📱 **iOS (TestFlight)**: [MinFox on TestFlight](https://testflight.apple.com/join/QaaEJKdy)
🤖 **Android (Google Play)**: [MinFox on Google Play](https://play.google.com/store/apps/details?id=com.minpox.minminisaas)

> Note: Some features shown in this repository may still be under development and may not yet be available in the app.

---

## 🔗 Related Projects

| | Project | Description |
|--|---------|-------------|
| 📱 | [min-minisaas-app](https://github.com/mink2mink2/min-minisaas-app) | MinFox Flutter mobile app (App Store) |
| ⚙️ | [min-minisaas-backend](https://github.com/mink2mink2/min-minisaas-backend) | FastAPI SaaS backend (GCP Cloud Run) |
| 🧠 | [min-mlops](https://github.com/mink2mink2/min-mlops) | ML model development workspace |
| 🌐 | [min-iot](https://github.com/mink2mink2/min-iot) | Full-stack IoT platform |
| 🤖 | [coinAI](https://github.com/mink2mink2/coinAI) | Cryptocurrency trading bot |

## License

MIT License — feel free to use this project as reference or learning material.
See [LICENSE](./LICENSE) for details.

---
---

<a name="korean"></a>

# 🏗️ min-minisaas-backend — SaaS 백엔드 API

> MinFox 앱을 구동하는 FastAPI 기반 백엔드 서버. 현재 테스트 및 개발 목적으로 GCP Cloud Run에 배포 중.

## 🚧 프로젝트 상태

**진행 중** — 이 프로젝트는 현재 활발히 개발 중이며, 아직 완성된 제품이 아닙니다.

이 백엔드는 앱 스토어에서 공개 테스트 중인 **MinFox (민폭스)** SaaS 앱을 구동하고 있습니다.

## 🤖 개발 방식

이 프로젝트는 제가 개념을 설계하고 방향을 결정했습니다.
대부분의 구현 코드는 AI 도구의 도움을 받아 작성되었습니다.

저의 역할은 생성된 코드를 검토하고, AI가 해결하지 못하는 문제를 찾아 수정하며, 전체 기능을 검증하는 것입니다.

앱이 실제 환경에서 테스트되는 동안 개발을 계속하고 있습니다.

---

## ⚠️ 공개 저장소 안내

이 저장소는 보안이 고려된 공개용 버전입니다.

보안상 중요한 설정 파일, 인증 정보, 배포 관련 설정은 모두 제거되어 있습니다.
따라서 저장소를 그대로 실행하면 바로 동작하지 않을 수 있습니다.

실행하려면 환경 변수 설정, 서비스 인증 정보, 인프라 설정 등이 추가로 필요합니다.
설정 예시는 `.env.example`을 참고하세요.

이 코드는 주로 아키텍처와 개발 구조를 공유하기 위한 목적으로 공개되었습니다.

---

## 🚀 빠른 시작

> 개발 환경 예시입니다. 실행을 위해 `.env` 설정 및 PostgreSQL, Redis, Firebase 인프라가 필요합니다.

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

**API 문서:** `http://localhost:8000/docs` (Swagger UI)

---

## 📝 개발

### DB 자동화 (최초 설치/업데이트)
```bash
# 최초 1회: DB 생성 + 마이그레이션 + 기본 카테고리 시드 + 런타임 검증
make setup

# 개별 실행
make bootstrap        # DB 없으면 생성
make migrate          # alembic upgrade head
make seed-categories  # board 기본 카테고리 멱등 시드
make seed-blog-categories  # blog 기본 카테고리 멱등 시드
make verify           # postgres/redis + 필수 스키마 점검 (실패 시 배포 중단)

# 운영/배포 전 DB 준비 (bootstrap 없이)
make release-prepare  # migrate + seed + verify
```

### Cloud Run startup DB prepare
- 컨테이너 기동 시 기본값으로 `alembic + seed`를 실행한 뒤 API를 시작합니다.
- 환경변수 `RUN_STARTUP_DB_PREPARE=false`를 주면 startup DB prepare를 건너뛸 수 있습니다.
- 환경변수 `RUN_STARTUP_DB_PREPARE_STRICT=true`면 prepare 실패 시 컨테이너를 종료합니다.

### DB 문서
- Migration 운영 절차: `docs/DB_MIGRATION_WORKFLOW.md`
- 현재 스키마 개요: `docs/DB_SCHEMA_OVERVIEW.md`

### Code Style
- **Format**: Black
- **Import Sort**: isort
- **Lint**: flake8, pylint
- 커밋/PR 시 GitHub Actions에서 자동 검사

---

## ⚡ 이벤트 드리븐 아키텍처

이 프로젝트는 **이벤트 기반 아키텍처**를 따릅니다.

### 원칙
- 모든 도메인 상태 변화는 이벤트로 발행
- 느슨한 결합을 통한 모듈 독립성 확보
- 이벤트 구독자들이 비즈니스 로직 처리

### 구현 상태 (2026-03-04)
- ✅ Board: posts, comments, likes (완전 구현)
- ✅ Chat: room, messages (완전 구현)
- ✅ Points: charge, consume, refund (완전 구현)
- ✅ PDF: file operations (완전 구현)
- 🟡 Blog: partial (create only)
- ❌ User profile updates (미구현)
- ❌ Blog updates/deletes/subscriptions (미구현)

---

---

## 📱 MinFox 앱 (공개 테스트)

이 프로젝트는 **MinFox 프로젝트 생태계**의 일부입니다.

이 저장소의 기능 중 일부는 **MinFox 모바일 앱**과 연동되어 있으며, 현재 **앱 스토어 공개 테스트 단계**에서 계속 개발 및 테스트가 진행되고 있습니다.

📱 **iOS (TestFlight)**: [MinFox on TestFlight](https://testflight.apple.com/join/QaaEJKdy)
🤖 **Android (Google Play)**: [MinFox on Google Play](https://play.google.com/store/apps/details?id=com.minpox.minminisaas)

> 참고: 일부 기능은 아직 개발 중이기 때문에 앱에 완전히 구현되지 않았을 수 있습니다.

---

## 🔗 관련 프로젝트

| | 프로젝트 | 설명 |
|--|---------|------|
| 📱 | [min-minisaas-app](https://github.com/mink2mink2/min-minisaas-app) | MinFox Flutter 모바일 앱 (앱 스토어) |
| ⚙️ | [min-minisaas-backend](https://github.com/mink2mink2/min-minisaas-backend) | FastAPI SaaS 백엔드 (GCP Cloud Run) |
| 🧠 | [min-mlops](https://github.com/mink2mink2/min-mlops) | ML 모델 개발 워크스페이스 |
| 🌐 | [min-iot](https://github.com/mink2mink2/min-iot) | 풀스택 IoT 플랫폼 |
| 🤖 | [coinAI](https://github.com/mink2mink2/coinAI) | 암호화폐 자동매매 봇 |

---

## 📄 라이선스

MIT 라이선스 — 참고 자료 또는 학습 목적으로 자유롭게 사용하세요.
자세한 내용은 [LICENSE](./LICENSE)를 참고하세요.
