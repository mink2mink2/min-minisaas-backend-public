"""Kakao 토큰 검증 및 사용자 정보 조회"""
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from app.core.config import settings


class KakaoVerifier:
    """Kakao 액세스 토큰 검증 및 사용자 정보 조회"""

    def __init__(self):
        self.user_info_url = "https://kapi.kakao.com/v2/user/me"
        self.token_info_url = "https://kapi.kakao.com/v1/user/access_token_info"
        self.rest_api_key = settings.KAKAO_REST_API_KEY

    async def verify(self, kakao_access_token: str) -> Dict[str, Any]:
        """
        Kakao 액세스 토큰 검증 및 사용자 정보 조회

        Args:
            kakao_access_token: Kakao 액세스 토큰

        Returns:
            사용자 정보 dict {
                user_id: str (Kakao UID),
                email: str,
                nickname: str,
                picture: str (프로필 이미지 URL)
            }

        Raises:
            HTTPException: 검증 실패 시
        """
        try:
            # 1. 토큰 유효성 검증
            token_info = await self._verify_token(kakao_access_token)

            # 2. 사용자 정보 조회
            user_info = await self._get_user_info(kakao_access_token)

            return {
                "user_id": str(user_info.get("id")),  # Kakao UID
                "email": user_info.get("kakao_account", {}).get("email"),
                "nickname": user_info.get("kakao_account", {}).get("profile", {}).get("nickname"),
                "picture": user_info.get("kakao_account", {}).get("profile", {}).get("profile_image_url"),
                "raw_data": user_info,  # 원본 데이터 저장 (메타데이터)
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(401, f"Kakao verification error: {str(e)}")

    async def _verify_token(self, kakao_access_token: str) -> Dict[str, Any]:
        """
        Kakao 토큰 유효성 검증

        Args:
            kakao_access_token: Kakao 액세스 토큰

        Returns:
            토큰 정보 dict
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {kakao_access_token}",
                }
                response = await client.get(self.token_info_url, headers=headers, timeout=10)

                if response.status_code == 401:
                    raise HTTPException(401, "Kakao token expired or invalid")
                elif response.status_code == 403:
                    raise HTTPException(403, "Kakao token verification forbidden")

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(401, "Kakao token invalid or expired")
            raise HTTPException(401, f"Kakao token verification failed: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(500, f"Kakao API connection error: {str(e)}")

    async def _get_user_info(self, kakao_access_token: str) -> Dict[str, Any]:
        """
        Kakao 사용자 정보 조회

        Args:
            kakao_access_token: Kakao 액세스 토큰

        Returns:
            사용자 정보 dict
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {kakao_access_token}",
                }
                params = {
                    "secure_resource": "true",  # HTTPS URL 반환
                }
                response = await client.get(
                    self.user_info_url,
                    headers=headers,
                    params=params,
                    timeout=10,
                )

                if response.status_code == 401:
                    raise HTTPException(401, "Kakao token expired or invalid")

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(401, "Kakao user info fetch failed: token invalid")
            raise HTTPException(401, f"Kakao API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(500, f"Kakao API connection error: {str(e)}")


kakao_verifier = KakaoVerifier()
