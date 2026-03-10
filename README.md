# Data Backup Microservice

The three endpoints are:

- `POST /backup/create`
- `GET /backup/list`
- `POST /backup/restore`

It uses only the Python standard library, so there are no external dependencies.

## What the service does

The service stores JSON backups on disk, one file per backup.
Each backup includes:

- `backup_id` (UUID)
- `created_at` (UTC ISO-8601 timestamp)
- `source_app`
- `user_id`
- `checksum` (SHA-256 of the backup data)
- `data` (the actual application data)


## Project structure

```text
data_backup_microservice/
├── backup_service/
│   ├── __init__.py
│   ├── auth.py
│   ├── config.py
│   ├── server.py
│   └── storage.py
├── backup_client.py
├── example_app_integration.py
└── README.md
```

## How to run the microservice

From the project folder:

```bash
python -m backup_service.server
```

By default, it starts at:

```text
http://127.0.0.1:8080
```

Default API key:

```text
dev-secret-key
```

## Optional environment variables

You can change configuration without editing code:

### Windows PowerShell

```powershell
$env:BACKUP_SERVICE_HOST="127.0.0.1"
$env:BACKUP_SERVICE_PORT="8080"
$env:BACKUP_SERVICE_DATA_DIR="./backups"
$env:BACKUP_SERVICE_API_KEYS="dev-secret-key,another-key"
python -m backup_service.server
```

### macOS/Linux

```bash
export BACKUP_SERVICE_HOST="127.0.0.1"
export BACKUP_SERVICE_PORT="8080"
export BACKUP_SERVICE_DATA_DIR="./backups"
export BACKUP_SERVICE_API_KEYS="dev-secret-key,another-key"
python -m backup_service.server
```

## API contract

### 1) Create backup

**Request**

```http
POST /backup/create
X-API-Key: dev-secret-key
Content-Type: application/json
```

```json
{
  "user_id": "user-123",
  "source_app": "CarLog",
  "data": {
    "vehicles": ["1987 Corvette"],
    "preferences": {"theme": "dark"}
  }
}
```

**Success response**

```json
{
  "status": "success",
  "message": "Backup created successfully",
  "backup": {
    "backup_id": "b5f0...",
    "user_id": "user-123",
    "source_app": "CarLog",
    "created_at": "2026-03-07T00:00:00+00:00",
    "checksum": "..."
  }
}
```

### 2) List backups

**Request**

```http
GET /backup/list?user_id=user-123
X-API-Key: dev-secret-key
```

**Success response**

```json
{
  "status": "success",
  "user_id": "user-123",
  "count": 1,
  "backups": [
    {
      "backup_id": "b5f0...",
      "created_at": "2026-03-07T00:00:00+00:00",
      "source_app": "CarLog",
      "checksum": "..."
    }
  ]
}
```

### 3) Restore backup

**Request**

```http
POST /backup/restore
X-API-Key: dev-secret-key
Content-Type: application/json
```

```json
{
  "user_id": "user-123",
  "backup_id": "b5f0..."
}
```

**Success response**

```json
{
  "status": "success",
  "message": "Backup restored successfully",
  "backup": {
    "backup_id": "b5f0...",
    "user_id": "user-123",
    "source_app": "CarLog",
    "created_at": "2026-03-07T00:00:00+00:00",
    "checksum": "..."
  },
  "data": {
    "vehicles": ["1987 Corvette"],
    "preferences": {"theme": "dark"}
  }
}
```

## Quick testing with curl

### Create a backup

```bash
curl -X POST http://127.0.0.1:8080/backup/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key" \
  -d '{
        "user_id": "user-123",
        "source_app": "CarLog",
        "data": {"vehicles": ["1987 Corvette"], "notes": "track setup"}
      }'
```

### List backups

```bash
curl "http://127.0.0.1:8080/backup/list?user_id=user-123" \
  -H "X-API-Key: dev-secret-key"
```

### Restore a backup

```bash
curl -X POST http://127.0.0.1:8080/backup/restore \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key" \
  -d '{
        "user_id": "user-123",
        "backup_id": "PUT-REAL-BACKUP-ID-HERE"
      }'
```

## How to integrate it into another program

#### Step 1: Decide what data to back up

For example, in `CarLog`, I might back up:

- user profile
- saved vehicles
- maintenance history
- modifications
- preferences

That becomes one Python dictionary.

```python
app_state = {
    "profile": {...},
    "vehicles": [...],
    "maintenance_records": [...],
    "preferences": {...}
}
```

#### Step 2: Call the service from your app

Use the included `BackupClient` helper:

```python
from backup_client import BackupClient

client = BackupClient(base_url="http://127.0.0.1:8080", api_key="dev-secret-key")

response = client.create_backup(
    user_id="user-123",
    source_app="CarLog",
    data=app_state,
)
print(response)
```

#### Step 3: Show available restore points in your UI

```python
backups = client.list_backups(user_id="user-123")
print(backups)
```

You would typically display:

- backup ID
- creation timestamp
- source app

#### Step 4: Restore selected backup

```python
restore_response = client.restore_backup(
    user_id="user-123",
    backup_id="the-backup-id-from-list"
)
restored_data = restore_response["data"]
```

#### Step 5: Write restored data back into your application

This depends on your main app.

Example:

```python
save_application_state(restored_data)
```

That exact pattern is shown in `example_app_integration.py`.

## How the included example works

Run this in a second terminal after the microservice is running:

```bash
python example_app_integration.py
```

It will:

1. create a small example app data file
2. create a backup through the microservice
3. list available backups
4. simulate corrupted app data
5. restore the backup
6. write restored data back into the example app file

## Error handling behavior

The service returns clear errors for:

- missing or invalid API key → `401 Unauthorized`
- missing fields / bad JSON / empty data → `400 Bad Request`
- invalid backup ID → `400 Bad Request`
- unknown routes → `404 Not Found`
