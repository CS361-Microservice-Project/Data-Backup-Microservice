from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .auth import ApiKeyAuth, AuthError
from .config import load_settings
from .storage import BackupError, BackupStorage


class BackupRequestHandler(BaseHTTPRequestHandler):
    server_version = "BackupService/1.0"

    def do_GET(self) -> None:
        try:
            self.server.auth.validate(self._headers_dict())
            parsed = urlparse(self.path)

            if parsed.path == "/health":
                self._write_json(HTTPStatus.OK, {"status": "ok"})
                return

            if parsed.path == "/backup/list":
                query = parse_qs(parsed.query)
                user_id = self._required_query_param(query, "user_id")
                backups = self.server.storage.list_backups(user_id)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "success",
                        "user_id": user_id,
                        "count": len(backups),
                        "backups": backups,
                    },
                )
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
        except AuthError as exc:
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
        except BackupError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception:
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Unexpected server error"})

    def do_POST(self) -> None:
        try:
            self.server.auth.validate(self._headers_dict())
            payload = self._read_json_body()

            if self.path == "/backup/create":
                user_id = self._required_field(payload, "user_id")
                source_app = self._required_field(payload, "source_app")
                if "data" not in payload:
                    raise BackupError("data is required")
                data = payload["data"]

                record = self.server.storage.create_backup(
                    user_id=user_id,
                    source_app=source_app,
                    data=data,
                )
                self._write_json(
                    HTTPStatus.CREATED,
                    {
                        "status": "success",
                        "message": "Backup created successfully",
                        "backup": {
                            "backup_id": record.backup_id,
                            "user_id": record.user_id,
                            "source_app": record.source_app,
                            "created_at": record.created_at,
                            "checksum": record.checksum,
                        },
                    },
                )
                return

            if self.path == "/backup/restore":
                user_id = self._required_field(payload, "user_id")
                backup_id = self._required_field(payload, "backup_id")
                record = self.server.storage.restore_backup(user_id=user_id, backup_id=backup_id)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "success",
                        "message": "Backup restored successfully",
                        "backup": {
                            "backup_id": record.backup_id,
                            "user_id": record.user_id,
                            "source_app": record.source_app,
                            "created_at": record.created_at,
                            "checksum": record.checksum,
                        },
                        "data": record.data,
                    },
                )
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
        except AuthError as exc:
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
        except BackupError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON"})
        except Exception:
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Unexpected server error"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise BackupError("Content-Length header is required")
        length = int(raw_length)
        body = self.rfile.read(length).decode("utf-8")
        if not body.strip():
            raise BackupError("Request body must not be empty")
        parsed = json.loads(body)
        if not isinstance(parsed, dict):
            raise BackupError("JSON body must be an object")
        return parsed

    def _headers_dict(self) -> dict[str, str]:
        return {key: value for key, value in self.headers.items()}

    @staticmethod
    def _required_field(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BackupError(f"{key} is required and must be a non-empty string")
        return value.strip()

    @staticmethod
    def _required_query_param(query: dict[str, list[str]], key: str) -> str:
        values = query.get(key, [])
        if not values or not values[0].strip():
            raise BackupError(f"Query parameter '{key}' is required")
        return values[0].strip()

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class BackupHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls, storage: BackupStorage, auth: ApiKeyAuth):
        super().__init__(server_address, handler_cls)
        self.storage = storage
        self.auth = auth


def run() -> None:
    settings = load_settings()
    storage = BackupStorage(settings.data_dir)
    auth = ApiKeyAuth(settings.api_keys)

    server = BackupHTTPServer(
        (settings.host, settings.port),
        BackupRequestHandler,
        storage=storage,
        auth=auth,
    )
    print(f"Backup service listening on http://{settings.host}:{settings.port}")
    print(f"Backup directory: {settings.data_dir.resolve()}")
    print("Configured API keys:", ", ".join(settings.api_keys))
    server.serve_forever()


if __name__ == "__main__":
    run()
