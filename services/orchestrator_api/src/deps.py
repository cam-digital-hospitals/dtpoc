from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from motor.core import Database
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

from .conf import MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_TIMEOUT_MS, MONGO_USER

client = AsyncIOMotorClient(
    host=MONGO_HOST,
    port=MONGO_PORT,
    username=MONGO_USER,
    password=MONGO_PASSWORD,
    timeoutMS=MONGO_TIMEOUT_MS,
)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    try:
        yield
    finally:
        client.close()


async def get_mongo_client() -> AsyncIOMotorClient:
    """Dependency for MongoDB client"""
    return client


async def get_orchestrator_database(
    client: AsyncIOMotorClient = Depends(get_mongo_client),
) -> Database:
    """Dependency for MongoDB orchestrator database"""
    return client.orchestrator


async def get_orchestrator_files_database(
    client: AsyncIOMotorClient = Depends(get_mongo_client),
) -> Database:
    """Dependency for MongoDB orchestrator_files database"""
    return client.orchestrator_files


async def get_gridfs_orchestrator_files(
    database: Database = Depends(get_orchestrator_files_database),
) -> AsyncIOMotorGridFSBucket:
    """Dependency for GridFS instance (orchestrator_files database)"""
    return AsyncIOMotorGridFSBucket(database)


async def get_kubernetes_api() -> AsyncIterator[k8s_client.ApiClient]:
    k8s_config.load_config()
    k8s_api = k8s_client.ApiClient()
    try:
        yield k8s_api
    finally:
        k8s_api.close()
