from pymongo import MongoClient

from .conf import MONGO_TIMEOUT_MS, MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USER


def get_database():
    try:
        client = MongoClient(
            host=MONGO_HOST,
            port=MONGO_PORT,
            username=MONGO_USER,
            password=MONGO_PASSWORD,
            timeoutMS=MONGO_TIMEOUT_MS,
        )
        yield client
    finally:
        if client:
            client.close()
