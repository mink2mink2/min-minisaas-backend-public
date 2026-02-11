"""Firebase JWT 검증"""
import httpx
from datetime import datetime
from typing import Dict, Any
from jose import jwt, JWTError, jwk
from fastapi import HTTPException
from app.core.config import settings


class FirebaseVerifier:
    """Firebase JWT 검증 및 캐싱"""

    def __init__(self):
        self.jwks_url = settings.FIREBASE_JWKS_URI
        self.project_id = settings.FIREBASE_PROJECT_ID
        self.public_keys: Dict[str, Any] = {}
        self.keys_updated_at = 0

    async def verify(self, token: str) -> Dict[str, Any]:
        """
        Firebase JWT 검증

        Args:
            token: Firebase JWT 토큰

        Returns:
            JWT payload dict

        Raises:
            HTTPException: 검증 실패 시
        """
        try:
            # 토큰 헤더 디코드 (서명 검증 없이)
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")

            if not kid:
                raise HTTPException(401, "Invalid Firebase token: missing kid")

            # Public key 조회 (캐시 확인)
            public_key = await self._get_public_key(kid)

            # JWT 검증
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.project_id,
            )

            # Firebase 토큰 필수 필드 검증
            if "sub" not in payload or "aud" not in payload:
                raise HTTPException(401, "Invalid Firebase token structure")

            return payload

        except JWTError as e:
            raise HTTPException(401, f"Firebase JWT verification failed: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(401, f"Firebase verification error: {str(e)}")

    async def _get_public_key(self, kid: str) -> str:
        """Public key 조회 (캐시 활용)"""
        # 캐시된 키 사용 (1시간마다 갱신)
        now = datetime.now().timestamp()
        if self.public_keys and (now - self.keys_updated_at) < 3600:
            if kid in self.public_keys:
                return self.public_keys[kid]

        # 새로운 키셋 다운로드
        await self._fetch_and_cache_keys()

        if kid not in self.public_keys:
            raise HTTPException(401, f"Firebase key not found: {kid}")

        return self.public_keys[kid]

    async def _fetch_and_cache_keys(self) -> None:
        """Google에서 Firebase public keys 다운로드 및 PEM 변환"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10)
                response.raise_for_status()

                keys_data = response.json()
                self.public_keys = {}

                for key_data in keys_data.get("keys", []):
                    kid = key_data.get("kid")
                    if kid:
                        try:
                            # JWKS format to PEM format
                            public_key = jwk.construct(key_data).to_pem()
                            self.public_keys[kid] = public_key.decode("utf-8") if isinstance(public_key, bytes) else public_key
                        except Exception:
                            continue

                self.keys_updated_at = datetime.now().timestamp()

        except Exception as e:
            raise HTTPException(500, f"Failed to fetch Firebase keys: {str(e)}")


firebase_verifier = FirebaseVerifier()
