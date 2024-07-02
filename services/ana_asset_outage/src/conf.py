import os

import pytz

env_get = os.environ.get

VERSION = env_get("VERSION", "v1")
HOST = env_get("HOST", "0.0.0.0")
PORT = int(env_get("PORT", "8000"))
MONGO_URI = env_get("MONGO_URI", "mongodb://localhost:27017")
MONGO_TIMEOUT_MS = int(env_get("MONGO_TIMEOUT_MS", "5000"))
TIMEZONE = pytz.timezone(env_get("TIMEZONE", "Europe/London"))
