from typing import Generator
from motor.motor_asyncio import AsyncIOMotorClient

from .conf import MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_TIMEOUT_MS, MONGO_USER

client = AsyncIOMotorClient(
    host=MONGO_HOST,
    port=MONGO_PORT,
    username=MONGO_USER,
    password=MONGO_PASSWORD,
    timeoutMS=MONGO_TIMEOUT_MS,
)

def get_mongo_client() -> AsyncIOMotorClient:
    """Dependency for MongoDB client"""
    return client