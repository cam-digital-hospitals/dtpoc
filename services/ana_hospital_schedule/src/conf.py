import os

env_get = os.environ.get

PORT = env_get("PORT", 8000)
MONGO_URI = env_get("MONGO_URI", "mongodb://localhost:27017")
