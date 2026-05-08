"""
HTTPX Client — async HTTP client for API testing.
Handles: auth, base URL, request/response logging, retries.
"""
import httpx
import structlog
from typing import Optional
from config.settings import settings

logger = structlog.get_logger(__name__)


class HonoAPIClient:
    def __init__(self):
        self.base_url = settings.hono_api_url
        self.api_key  = settings.hono_api_key
        self._token:  Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Content-Type": "application/json",
                "x-api-key":    self.api_key,
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def login(self, email: str, password: str) -> str:
        """Login and store Bearer token. Returns token."""
        response = await self._client.post(
            "/v1/users/login",
            json={"email": email, "password": password},
        )
        logger.info("api_login", status=response.status_code)
        response.raise_for_status()

        data  = response.json()
        token = (data.get("data", {}) or {}).get("accessToken") or \
                (data.get("data", {}) or {}).get("token") or \
                data.get("accessToken") or data.get("token")

        if not token:
            # Try to find token in nested structure
            import json
            logger.debug("login_response", body=json.dumps(data)[:200])
            raise ValueError(f"Token not found in response. Keys: {list(data.keys())}")

        self._token = token
        self._client.headers["Authorization"] = f"Bearer {token}"
        logger.info("api_login_success")
        return token

    async def get(self, path: str, params: dict = None) -> httpx.Response:
        resp = await self._client.get(path, params=params)
        logger.info("api_get", path=path, status=resp.status_code)
        return resp

    async def post(self, path: str, json: dict = None) -> httpx.Response:
        resp = await self._client.post(path, json=json)
        logger.info("api_post", path=path, status=resp.status_code)
        return resp

    async def put(self, path: str, json: dict = None) -> httpx.Response:
        resp = await self._client.put(path, json=json)
        logger.info("api_put", path=path, status=resp.status_code)
        return resp

    async def delete(self, path: str) -> httpx.Response:
        resp = await self._client.delete(path)
        logger.info("api_delete", path=path, status=resp.status_code)
        return resp
