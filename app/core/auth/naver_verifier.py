"""네이버 토큰 검증 및 사용자 정보 조회"""
import httpx
from typing import Dict, Any
from app.core.exceptions import AuthException
from app.core.config import settings


class NaverVerifier:
    """네이버 액세스 토큰 검증 및 사용자 정보 조회"""

    def __init__(self):
        self.user_info_url = "https://openapi.naver.com/v1/nid/me"
        self.client_id = settings.NAVER_CLIENT_ID
        self.client_secret = settings.NAVER_CLIENT_SECRET

    async def verify(self, naver_access_token: str) -> Dict[str, Any]:
        """
        네이버 액세스 토큰 검증 및 사용자 정보 조회

        Args:
            naver_access_token: 네이버 액세스 토큰

        Returns:
            사용자 정보 dict {
                user_id: str (네이버 UID),
                email: str,
                nickname: str,
                picture: str (프로필 이미지 URL)
            }

        Raises:
            HTTPException: 검증 실패 시
        """
        try:
            # 사용자 정보 조회
            user_info = await self._get_user_info(naver_access_token)

            return {
                "user_id": user_info.get("id"),  # 네이버 UID
                "email": user_info.get("email"),
                "nickname": user_info.get("nickname"),
                "picture": user_info.get("profile_image"),
                "raw_data": user_info,  # 원본 데이터 저장 (메타데이터)
            }

        except AuthException:
            raise
        except Exception as e:
            raise AuthException("AUTHENTICATION_FAILED", 401)

    async def _get_user_info(self, naver_access_token: str) -> Dict[str, Any]:
        """
        네이버 사용자 정보 조회

        Args:
            naver_access_token: 네이버 액세스 토큰

        Returns:
            사용자 정보 dict (response.response 안의 데이터)
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {naver_access_token}",
                    "X-Naver-Client-Id": self.client_id,
                    "X-Naver-Client-Secret": self.client_secret,
                }
                response = await client.get(
                    self.user_info_url,
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 401:
                    raise AuthException("INVALID_TOKEN", 401)
                elif response.status_code == 403:
                    raise AuthException("INVALID_TOKEN", 401)

                response.raise_for_status()
                
                # Naver API response: { "resultcode": "00", "message": "success", "response": {...} }
                data = response.json()
                
                if data.get("resultcode") != "00":
                    raise AuthException("AUTHENTICATION_FAILED", 401)

                return data.get("response", {})

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthException("INVALID_TOKEN", 401)
            raise AuthException("AUTHENTICATION_FAILED", 401)
        except httpx.RequestError as e:
            raise AuthException("AUTHENTICATION_FAILED", 401)


naver_verifier = NaverVerifier()
