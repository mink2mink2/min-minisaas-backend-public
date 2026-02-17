# Backend CI/CD & Cloud Run Deployment Guide

**Last Updated:** Feb 17, 2026
**Status:** Ready for GCP Setup
**Target Environment:** Google Cloud Run (asia-northeast1 / Japan)

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
Docker Build → Artifact Registry (asia-northeast1)
    ↓
Cloud Run Service (asia-northeast1)
    ↓
VPC Connector → VPC Network → Cloud SQL (Fixed IP)
    ↓
Cloudflare DNS (api.minpox.com) → Cloud Run Service
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
- **Region:** asia-northeast1 (hardcoded in workflow)

---

## 🔧 GitHub Secrets Setup

You must set these 3 secrets in your GitHub repository:

### 1. GCP_PROJECT_ID
- **Value:** Your GCP project ID (e.g., `minisaas-japan-prod`)
- **Where to find:**
  - Go to Google Cloud Console
  - Click project selector (top-left)
  - Copy the Project ID field

### 2. GCP_SA_KEY
- **Value:** Full JSON content of Service Account key
- **Steps to create:**
  1. Google Cloud Console → IAM and Admin → Service Accounts
  2. Create new service account (name: `min-minisaas-backend-ci`)
  3. Grant these roles:
     - `Cloud Run Developer`
     - `Artifact Registry Writer`
     - `Compute Network User` (for VPC Connector)
  4. Create JSON key
  5. Copy entire JSON content to GitHub Secret

### 3. VPC_CONNECTOR_NAME
- **Value:** Name of your Serverless VPC Connector (e.g., `asia-northeast1-vpc-connector`)
- **Where to find:**
  - Google Cloud Console → VPC Network → Serverless VPC Connectors
  - Copy the connector name for asia-northeast1

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
  - Region: `asia-northeast1`
  - Network: [your VPC name]
  - IP range: ___________________

- [ ] **Artifact Registry Repository**
  - Repository name: `min-minisaas-backend`
  - Region: `asia-northeast1`
  - Format: `Docker`

- [ ] **Cloud SQL (Database)**
  - Instance name: ___________________
  - VPC Network: [your VPC name]
  - Private IP: ___________________
  - Public IP: NONE (private connectivity only)

- [ ] **Service Account**
  - Name: `min-minisaas-backend-ci`
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
    "project_id": "minisaas-japan-prod",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "min-minisaas-backend-ci@minisaas-japan-prod.iam.gserviceaccount.com",
    ...
  }
  ```

#### Secret #3: VPC_CONNECTOR_NAME
- **Name:** `VPC_CONNECTOR_NAME`
- **Value:** (Your VPC Connector name, e.g., `asia-northeast1-vpc-connector`)

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
DATABASE_URL=postgresql+asyncpg://user:password@[PRIVATE_IP]:5432/minisaas_db

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
   gcloud run services describe min-minisaas-backend \
     --region asia-northeast1 \
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

### Connect api.minpox.com to Cloud Run

1. **Get Cloud Run service URL**
   ```bash
   gcloud run services describe min-minisaas-backend \
     --region asia-northeast1 \
     --format 'value(status.url)'
   # Returns: https://min-minisaas-backend-[hash].a.run.app
   ```

2. **In Cloudflare Dashboard**
   - DNS → Add Record
   - Type: `CNAME`
   - Name: `api`
   - Content: `min-minisaas-backend-[hash].a.run.app`
   - Proxy status: `Proxied` (Orange cloud)
   - TTL: Auto

3. **Enable HTTPS**
   - Cloudflare automatically provisions SSL/TLS
   - Cloud Run provides HTTPS by default
   - Combined = Full HTTPS chain

4. **Test custom domain**
   ```bash
   curl https://api.minpox.com/health
   # Should return: {"status": "ok"}
   ```

---

## 📊 Cloud Run Configuration Details

### Service Settings (Automated by GitHub Actions)

- **Service Name:** `min-minisaas-backend`
- **Region:** `asia-northeast1` (Tokyo)
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
gcloud run services logs read min-minisaas-backend \
  --region asia-northeast1 \
  --limit 50

# Filter errors
gcloud run services logs read min-minisaas-backend \
  --region asia-northeast1 \
  --limit 50 | grep -i error

# Real-time logs
gcloud run services logs read min-minisaas-backend \
  --region asia-northeast1 \
  --follow
```

### Cloud Logging Dashboard

- Google Cloud Console → Cloud Logging
- Filter by service: `resource.service.name="min-minisaas-backend"`
- View structured logs, errors, performance metrics

---

## 🛠️ Troubleshooting

### 403 Forbidden on Artifact Registry

**Cause:** Service Account lacks `Artifact Registry Writer` role

**Fix:**
```bash
gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member=serviceAccount:min-minisaas-backend-ci@[PROJECT_ID].iam.gserviceaccount.com \
  --role=roles/artifactregistry.writer
```

### VPC Connector Connection Failed

**Cause:** VPC Connector name incorrect or VPC network mismatch

**Fix:**
1. Verify VPC Connector exists in asia-northeast1
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
- `GCP_REGION` → Hardcoded: `asia-northeast1`
- `SERVICE_NAME` → Hardcoded: `min-minisaas-backend`
- `REGISTRY_HOSTNAME` → Hardcoded: `asia-northeast1-docker.pkg.dev`

**Key Secrets Used:**
- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `VPC_CONNECTOR_NAME`

---

## ✅ Deployment Checklist

Before first deployment:

- [ ] GCP Project created
- [ ] VPC Network + Cloud Router + Cloud NAT configured
- [ ] Serverless VPC Connector created in asia-northeast1
- [ ] Artifact Registry repository created
- [ ] Cloud SQL configured with Private IP in same VPC
- [ ] Service Account created with proper roles
- [ ] Service Account JSON key ready
- [ ] GitHub Secrets configured (3 secrets)
- [ ] `.env.production` created with all values
- [ ] Dockerfile exists
- [ ] GitHub Actions workflow exists
- [ ] Custom domain ready (api.minpox.com in Cloudflare)

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
gcloud run services describe min-minisaas-backend \
  --region asia-northeast1 \
  --format 'value(status.url)'

# Test service health
curl https://api.minpox.com/health
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
