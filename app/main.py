"""FastAPI 앱"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.cache import cache
from app.core.exceptions import AuthException, auth_exception_handler

app = FastAPI(title="min-minisaas", version="0.1.0")

# Register exception handler for unified auth errors
app.add_exception_handler(AuthException, auth_exception_handler)

@app.on_event("startup")
async def startup():
    await cache.init()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}