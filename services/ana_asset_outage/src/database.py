from pymongo import MongoClient

from .conf import MONGO_URI


def get_database():
    try:
        client = MongoClient(MONGO_URI)
        yield client
    finally:
        if client:
            client.close()
