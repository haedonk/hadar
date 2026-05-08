import os
import sys
from pathlib import Path

# Ensure DATABASE_URL is set before any service-side modules import db.session,
# which evaluates create_async_engine() at module load. The URL just needs to
# parse cleanly — no real connection is attempted during these tests.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
os.environ.setdefault("MQTT_HOST", "localhost")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVICE_ROOT.parent

for path in (str(SERVICE_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
