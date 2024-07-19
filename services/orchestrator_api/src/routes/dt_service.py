import json
import tempfile
import time
import logging
from typing import Dict, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, responses
from kubernetes import client as k8s_client
from kubernetes.client import ApiException
from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from ..deps import get_gridfs_orchestrator_files, get_kubernetes_api, get_orchestrator_database
from ..models import ServiceLaunchRequest, ServiceLaunchResponse

router = APIRouter(prefix="/service", tags=["core"])
logger = logging.getLogger(__name__)


async def get_service_status(
    service_id: str, k8s_api_client: k8s_client.ApiClient
) -> str:
    api_instance = k8s_client.BatchV1Api(k8s_api_client)
    namespace = "default"
    try:
        job = api_instance.read_namespaced_job(
            namespace=namespace,
            name=service_id,
        )

        active_runs = job.status.active if job.status.active is not None else 0
        succeeded_runs = job.status.succeeded if job.status.succeeded is not None else 0
        failed_runs = job.status.failed if job.status.failed is not None else 0

        total_runs = succeeded_runs + failed_runs + active_runs

        if succeeded_runs > 0 and active_runs == 0 and failed_runs == 0:
            status = "ok"
        elif active_runs > 0:
            status = "running"
        else:
            status = "error"

        return dict(
            active_runs=active_runs,
            succeeded_runs=succeeded_runs,
            failed_runs=failed_runs,
            total_runs=total_runs,
            status=status,
        )
    except ApiException as e:
        logger.error(f"Exception when retrieving custom resource status: {e}")
        raise e


@router.get("/")
async def list_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    db: AgnosticDatabase = Depends(get_orchestrator_database),
    k8s_api_client: k8s_client.ApiClient = Depends(get_kubernetes_api),
) -> List[Dict]:
    services_collection = db.services
    services = (
        await services_collection.find().skip(skip).limit(limit).to_list(length=limit)
    )
    service_list = []
    
    for service in services:
        service_id = str(service.get("_id"))
        service_status = await get_service_status(service_id, k8s_api_client)
        service_record = {
            "id": service_id,
            "image": service.get("image"),
            "version": service.get("version"),
            "description": service.get("description"),
            "reps": service.get("reps"),
            "mount_files": service.get("mount_files"),
            "output_files": service.get("output_files"),
            "created_at": service.get("created_at"),
            **service_status,
        }
        service_list.append(service_record)
    logger.info(
        f"Listed {len(service_list)} services with skip={skip} and limit={limit}."
    )
    return service_list


@router.post(
    "/launch",
    response_model=ServiceLaunchResponse,
    status_code=202,
)
async def launch_service(
    data: ServiceLaunchRequest,
    db: AgnosticDatabase = Depends(get_orchestrator_database),
    k8s_api_client: k8s_client.ApiClient = Depends(get_kubernetes_api),
):
    """Launch a DT service."""
    try:
        # TODO
        if data.ana is None:
            logger.error("Implementation for other modules not defined.")
            raise NotImplementedError("Implementation for other modules not defined.")

        # TODO: change this
        # find a convention for namespaces (namespace per DT Solution?)
        namespace = "default"

        services_collection = db.services
        service_record = {
            "image": data.image,
            "version": data.version,
            "description": data.description,
            "mount_files": data.mount_files,
            "reps": data.ana.reps,
            "env": data.env,
            "env": data.env,
            "created_at": time.time(),
        }
        result = await services_collection.insert_one(service_record)
        service_id = str(result.inserted_id)
        logger.info(f"Service record created with ID: {service_id}")

        body = {
            "apiVersion": "eng.cam.ac.uk/v1alpha1",
            "kind": "Analytics",
            "metadata": {"name": service_id},
            "spec": {
                "image": f"{data.image}:{data.version}",
                "description": data.description,
                "jobType": data.ana.job_type,
                "port": data.port,
                "schedule": data.ana.schedule,
                "reps": data.ana.reps,
                "env": data.env,
            },
        }

        api_instance = k8s_client.CustomObjectsApi(k8s_api_client)
        api_response = api_instance.create_namespaced_custom_object(
            group="eng.cam.ac.uk",
            version="v1alpha1",
            namespace=namespace,
            plural="analytics",
            body=body,
        )
        logger.info(f"Custom resource created in Kubernetes with ID: {service_id}")

        return ServiceLaunchResponse(id=service_id)

    except ApiException as e:
        logger.error(f"Exception when creating custom resource: {e}")
        raise HTTPException(
            status_code=e.status, detail=f"Exception when creating custom resource: {e}"
        )

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.get(
    "/{id}/status",
)
async def service_status(
    id: str,
    db: AgnosticDatabase = Depends(get_orchestrator_database),
    k8s_api_client: k8s_client.ApiClient = Depends(get_kubernetes_api),
):
    """Get the status of a DT service."""
    logger.info("Fetching service status")
    services_collection = db.services
    service = await services_collection.find_one({"_id": ObjectId(id)})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found in database")

    service_id = str(service.get("_id"))
    serviceStatus = await get_service_status(service_id, k8s_api_client)

    return {
        "active_runs": serviceStatus.get("active_runs"),
        "succeeded_runs": serviceStatus.get("succeeded_runs"),
        "failed_runs": serviceStatus.get("failed_runs"),
        "total_runs": serviceStatus.get("total_runs"),
        "status": serviceStatus.get("status"),
        "output_files": list(service.get("output_files").keys())
    }


@router.get(
    "/{id}/output/{idx}",
)
async def service_output(
    id: str,
    idx: int,
    db: AgnosticDatabase = Depends(get_orchestrator_database),
    k8s_api_client: k8s_client.ApiClient = Depends(get_kubernetes_api),
    fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_orchestrator_files),
):
    """Get the output of a multirun job, if any."""
    logger.info("Fetching service output")
    services_collection = db.services
    service = await services_collection.find_one({"_id": ObjectId(id)})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found in database")
    
    output_files = service.get('output_files')
    if not output_files or idx >= len(output_files):
        raise HTTPException(status_code=404, detail="Output file not found")
    requested_file_id = list(output_files.keys())[idx]

    data = {}
    try:
        with tempfile.TemporaryFile("wb+") as tmp:
            await fs.download_to_stream(ObjectId(requested_file_id), tmp)
            tmp.seek(0)
            data = json.load(tmp)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail="Error downloading file")

    return responses.JSONResponse(content=data)



@router.delete(
    "/{id}/terminate",
)
async def terminate_service(
    id: str,
    db: AgnosticDatabase = Depends(get_orchestrator_database),
    k8s_api_client: k8s_client.ApiClient = Depends(get_kubernetes_api),
):
    """Terminate a DT service."""
    try:
        try:
            logger.info("Terminating service")
            # Delete the custom resource from Kubernetes
            api_instance = k8s_client.CustomObjectsApi(k8s_api_client)
            namespace = "default"  # Change this as needed
            api_response = api_instance.delete_namespaced_custom_object(
                group="eng.cam.ac.uk",
                version="v1alpha1",
                namespace=namespace,
                plural="analytics",
                name=id,
                body=k8s_client.V1DeleteOptions(),
            )
            logger.info(f"Custom resource with ID {id} deleted from Kubernetes")

        except ApiException as e:
            logger.error(f"Exception when deleting custom resource: {e}")
            # raise HTTPException(
            #     status_code=e.status, detail=f"Exception when deleting custom resource: {e}"
            # )

        # Delete the service record from MongoDB
        services_collection = db.services
        result = await services_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Service not found in database")
        logger.info(f"Service record with ID {id} deleted from MongoDB")

        return {"message": "Service terminated successfully"}
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
