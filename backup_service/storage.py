from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class BackupError(Exception):
    """Raised for expected backup service failures."""


@dataclass(frozen=True)
class BackupRecord:
    backup_id: str
    user_id: str
    source_app: str
    created_at: str
    checksum: str
    data: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "user_id": self.user_id,
            "source_app": self.source_app,
            "created_at": self.created_at,
            "checksum": self.checksum,
            "data": self.data,
        }


class BackupStorage:
    """Filesystem-backed storage with atomic writes and checksum validation."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def create_backup(self, user_id: str, source_app: str, data: Any) -> BackupRecord:
        if not user_id.strip():
            raise BackupError("user_id must not be empty")
        if not source_app.strip():
            raise BackupError("source_app must not be empty")
        if data in (None, "", [], {}):
            raise BackupError("backup data must not be empty")

        backup_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        checksum = self._checksum(data)
        record = BackupRecord(
            backup_id=backup_id,
            user_id=user_id,
            source_app=source_app,
            created_at=created_at,
            checksum=checksum,
            data=data,
        )

        path = self._backup_path(user_id, backup_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self._atomic_write_json(path, record.to_dict())

        return record

    def list_backups(self, user_id: str) -> list[dict[str, Any]]:
        user_dir = self.base_dir / user_id
        if not user_dir.exists():
            return []

        results: list[dict[str, Any]] = []
        for path in sorted(user_dir.glob("*.json"), key=lambda p: p.name, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise BackupError(f"Corrupted backup metadata in {path.name}") from exc

            results.append(
                {
                    "backup_id": payload["backup_id"],
                    "created_at": payload["created_at"],
                    "source_app": payload["source_app"],
                    "checksum": payload["checksum"],
                }
            )
        results.sort(key=lambda item: item["created_at"], reverse=True)
        return results

    def restore_backup(self, user_id: str, backup_id: str) -> BackupRecord:
        path = self._backup_path(user_id, backup_id)
        if not path.exists():
            raise BackupError("backup_id was not found")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BackupError("Stored backup could not be decoded") from exc

        actual_checksum = self._checksum(payload["data"])
        if actual_checksum != payload["checksum"]:
            raise BackupError("Stored backup failed checksum verification")

        return BackupRecord(
            backup_id=payload["backup_id"],
            user_id=payload["user_id"],
            source_app=payload["source_app"],
            created_at=payload["created_at"],
            checksum=payload["checksum"],
            data=payload["data"],
        )

    def _backup_path(self, user_id: str, backup_id: str) -> Path:
        safe_user_id = self._sanitize_segment(user_id)
        safe_backup_id = self._sanitize_segment(backup_id)
        return self.base_dir / safe_user_id / f"{safe_backup_id}.json"

    @staticmethod
    def _sanitize_segment(value: str) -> str:
        allowed = {"-", "_"}
        cleaned = "".join(ch for ch in value if ch.isalnum() or ch in allowed)
        if not cleaned:
            raise BackupError("Identifier contained no safe characters")
        return cleaned

    @staticmethod
    def _checksum(data: Any) -> str:
        normalized = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        directory = path.parent
        fd, temp_name = tempfile.mkstemp(prefix="backup_", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.remove(temp_name)
