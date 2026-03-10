from __future__ import annotations

from typing import Iterable


class AuthError(Exception):
    """Raised when API authentication fails."""


class ApiKeyAuth:
    def __init__(self, valid_api_keys: Iterable[str]) -> None:
        self.valid_api_keys = {key.strip() for key in valid_api_keys if key and key.strip()}

    def validate(self, headers: dict[str, str]) -> str:
        api_key = self._extract_key(headers)
        if not api_key or api_key not in self.valid_api_keys:
            raise AuthError("Missing or invalid API key")
        return api_key

    @staticmethod
    def _extract_key(headers: dict[str, str]) -> str | None:
        if "X-API-Key" in headers:
            return headers["X-API-Key"]

        authorization = headers.get("Authorization", "")
        prefix = "Bearer "
        if authorization.startswith(prefix):
            return authorization[len(prefix):].strip()
        return None
