from __future__ import annotations

import json
from pathlib import Path

from backup_client import BackupClient


BASE_DIR = Path(__file__).resolve().parent
APP_DATA_FILE = BASE_DIR / "example_app_data.json"


def load_application_state() -> dict:
    if not APP_DATA_FILE.exists():
        starter = {
            "profile": {"name": "John", "email": "user@example.com"},
            "vehicles": ["1987 Corvette"],
            "preferences": {"theme": "dark"},
        }
        save_application_state(starter)
        return starter

    return json.loads(APP_DATA_FILE.read_text(encoding="utf-8"))


def save_application_state(state: dict) -> None:
    APP_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    print(APP_DATA_FILE)
    print(APP_DATA_FILE.parent.exists())

    APP_DATA_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> None:
    client = BackupClient(base_url="http://127.0.0.1:8080", api_key="dev-secret-key")
    user_id = "user-123"
    source_app = "CarLog"

    current_state = load_application_state()
    print("Current app state:")
    print(json.dumps(current_state, indent=2))

    print("\nCreating backup...")
    create_response = client.create_backup(
        user_id=user_id,
        source_app=source_app,
        data=current_state,
    )
    print(json.dumps(create_response, indent=2))

    print("\nListing backups...")
    list_response = client.list_backups(user_id=user_id)
    print(json.dumps(list_response, indent=2))

    if not list_response.get("backups"):
        raise RuntimeError("No backups were returned by the service.")

    backup_id = list_response["backups"][0]["backup_id"]

    print("\nPretending the app data was corrupted...")
    corrupted_state = {"profile": {}, "vehicles": [], "preferences": {"theme": "broken"}}
    save_application_state(corrupted_state)
    print(json.dumps(load_application_state(), indent=2))

    print("\nRestoring backup into the application...")
    restore_response = client.restore_backup(user_id=user_id, backup_id=backup_id)
    restored_data = restore_response["data"]
    save_application_state(restored_data)

    print("\nFinal application state after restore:")
    print(json.dumps(load_application_state(), indent=2))


if __name__ == "__main__":
    main()