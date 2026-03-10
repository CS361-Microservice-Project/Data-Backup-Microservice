from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BackupClientError(Exception):
    """Raised when backup service returns an error."""


@dataclass
class BackupClient:
    base_url: str
    api_key: str
    timeout_seconds: int = 10

    def create_backup(self, user_id: str, source_app: str, data: Any) -> dict[str, Any]:
        return self._post(
            "/backup/create",
            {
                "user_id": user_id,
                "source_app": source_app,
                "data": data,
            },
        )

    def list_backups(self, user_id: str) -> dict[str, Any]:
        query = urlencode({"user_id": user_id})
        return self._get(f"/backup/list?{query}")

    def restore_backup(self, user_id: str, backup_id: str) -> dict[str, Any]:
        return self._post(
            "/backup/restore",
            {
                "user_id": user_id,
                "backup_id": backup_id,
            },
        )

    def _get(self, path: str) -> dict[str, Any]:
        request = Request(
            self.base_url + path,
            headers=self._headers(),
            method="GET",
        )
        return self._execute(request)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url + path,
            headers=self._headers(),
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        return self._execute(request)

    def _execute(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            try:
                parsed = json.loads(error_body)
                message = parsed.get("error", error_body)
            except json.JSONDecodeError:
                message = error_body
            raise BackupClientError(f"HTTP {exc.code}: {message}") from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
