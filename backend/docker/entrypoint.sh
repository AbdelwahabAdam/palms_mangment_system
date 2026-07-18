#!/bin/sh
set -eu

echo "Running database migrations..."
alembic upgrade head

echo "Ensuring object storage bucket..."
python - <<'PY'
from palms_api.config import get_settings
from palms_api.storage import build_storage_client

settings = get_settings()
client = build_storage_client(settings)
for attempt in range(1, 16):
    try:
        client.ensure_bucket()
        print(f"storage_ready attempt={attempt}")
        break
    except Exception as error:  # noqa: BLE001 - retry until MinIO is ready
        if attempt == 15:
            raise
        print(f"storage_wait attempt={attempt} error={error}")
        import time
        time.sleep(2)
PY

echo "Starting RQ worker..."
rq worker "${RQ_QUEUE_NAME:-reports}" --url "${REDIS_URL}" &

echo "Starting report scheduler loop..."
(
  while true; do
    palms-report-scheduler || true
    sleep 60
  done
) &

echo "Starting API server on :8000..."
exec waitress-serve --listen=0.0.0.0:8000 palms_api.wsgi:application
