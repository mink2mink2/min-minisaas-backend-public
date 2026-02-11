import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_security_flow():
    async with httpx.AsyncClient() as client:
        # 1. Register (if not exists, ignore error if already exists)
        email = "test_security@example.com"
        password = "password123"
        await client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})

        # 2. Login as "app" (spoofing or real)
        print("\n[1] Logging in as 'app'...")
        login_resp = await client.post(
            f"{BASE_URL}/auth/login", 
            json={"email": email, "password": password, "client_type": "app"},
            headers={"User-Agent": "MySecureApp/1.0"}
        )
        login_data = login_resp.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        print(f"Tokens received. Access length: {len(access_token)}")

        # 3. Access protected endpoint
        print("\n[2] Accessing /users/me...")
        me_resp = await client.get(
            f"{BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": "MySecureApp/1.0"}
        )
        print(f"Status: {me_resp.status_code}, Data: {me_resp.json()}")

        # 4. Refresh token
        print("\n[3] Refreshing token (Rotation test)...")
        refresh_resp = await client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"User-Agent": "MySecureApp/1.0"}
        )
        refresh_data = refresh_resp.json()
        new_access = refresh_data["access_token"]
        new_refresh = refresh_data["refresh_token"]
        print("Token rotated successfully.")

        # 5. Try to use OLD refresh token again (should fail)
        print("\n[4] Reusing OLD refresh token (Security check)...")
        fail_resp = await client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"User-Agent": "MySecureApp/1.0"}
        )
        print(f"Old refresh status (expected 401): {fail_resp.status_code}")
        
        # 6. Check if session is still valid with NEW access token
        print("\n[5] Accessing /users/me with NEW access token...")
        me_new_resp = await client.get(
            f"{BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {new_access}", "User-Agent": "MySecureApp/1.0"}
        )
        print(f"Status: {me_new_resp.status_code}, Data: {me_new_resp.json()}")

if __name__ == "__main__":
    try:
        asyncio.run(test_security_flow())
    except Exception as e:
        print(f"Test failed: {e}")
