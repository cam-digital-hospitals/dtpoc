import os

env_get = os.environ.get

VERSION = env_get("VERSION", "v1alpha1")
HOST = env_get("HOST", "0.0.0.0")
PORT = int(env_get("PORT", "8000"))
MONGO_HOST = env_get("MONGO_HOST", "localhost")
MONGO_PORT = int(env_get("MONGO_PORT", "27017"))
MONGO_USER = env_get("MONGO_USER", "root")
MONGO_PASSWORD = env_get("MONGO_PASSWORD", "password")
MONGO_TIMEOUT_MS = int(env_get("MONGO_TIMEOUT_MS", "5000"))
