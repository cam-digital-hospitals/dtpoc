import logging
from typing import Annotated
import hashlib

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from motor.core import AgnosticDatabase

from ..deps import get_gridfs_orchestrator_files, get_orchestrator_files_database

router = APIRouter(tags=["files"])
logger = logging.getLogger(__name__)


def compute_file_hash(file):
    hasher = hashlib.md5()
    file.seek(0)
    while chunk := file.read(8192):
        hasher.update(chunk)
    file.seek(0)
    return hasher.hexdigest()


@router.get("/files")
async def list_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    files_db: AsyncIOMotorGridFSBucket = Depends(get_gridfs_orchestrator_files),
    fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_orchestrator_files),
):
    try:
        cursor = fs.find().skip(skip).limit(limit)
        files = []
        async for file_doc in cursor:
            files.append(
                {
                    "file_id": str(file_doc._id),
                    "filename": file_doc.filename,
                    "length": file_doc.length,
                    "uploadDate": file_doc.uploadDate,
                    "metadata": file_doc.metadata,
                }
            )
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/files/upload")
async def upload_file(
    file: Annotated[UploadFile, File(description="A file to upload")],
    files_db: AgnosticDatabase = Depends(get_orchestrator_files_database),
    fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_orchestrator_files),
):
    try:
        # Compute the file hash
        file_hash = compute_file_hash(file.file)
        logger.info(f"Computed hash for file {file.filename}: {file_hash}")

        # Check for a file with the same hash
        existing_file = await files_db['fs.files'].find_one(
            {
                "metadata.hash": file_hash,
            }
        )

        if existing_file:
            logger.info(
                f"File {file.filename} already exists with ID {existing_file['_id']}"
            )
            return {
                "file_id": str(existing_file['_id']),
                "filename": file.filename,
                "message": "File already exists",
            }

        file_id = await fs.upload_from_stream(
            file.filename, file.file, metadata={"hash": file_hash}
        )
        logger.info(f"Uploaded file {file.filename} with ID {file_id}")
        return {"file_id": str(file_id), "filename": file.filename}
    except Exception as e:
        logger.error(
            f"An error occurred while uploading file {file.filename}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.get("/files/{file_id}")
async def get_file(
    file_id: str, fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_orchestrator_files)
):
    try:
        file_id = ObjectId(file_id)
        stream = await fs.open_download_stream(file_id)
        headers = {"Content-Disposition": f"attachment; filename={stream.filename}"}
        return StreamingResponse(
            stream, headers=headers, media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str, fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_orchestrator_files)
):
    try:
        file_id = ObjectId(file_id)
        await fs.delete(file_id)
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
