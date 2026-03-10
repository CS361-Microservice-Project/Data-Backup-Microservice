from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    api_keys: list[str]


def load_settings() -> Settings:
    host = os.getenv("BACKUP_SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("BACKUP_SERVICE_PORT", "8080"))
    data_dir = Path(os.getenv("BACKUP_SERVICE_DATA_DIR", "./backups"))

    raw_keys = os.getenv("BACKUP_SERVICE_API_KEYS", "dev-secret-key")
    api_keys = [key.strip() for key in raw_keys.split(",") if key.strip()]

    return Settings(
        host=host,
        port=port,
        data_dir=data_dir,
        api_keys=api_keys,
    )
