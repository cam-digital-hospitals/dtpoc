import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from kubernetes import client as k8s_client
from kubernetes.client import ApiException
from motor.core import AgnosticDatabase

from ..deps import get_kubernetes_api, get_orchestrator_database
from ..models import ServiceLaunchRequest, ServiceLaunchResponse

router = APIRouter(tags=["core"])
logger = logging.getLogger(__name__)


@router.post(
    "/launch",
    response_model=ServiceLaunchResponse,
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

        services_collection = db.services
        service_record = {
            "image": data.image,
            "version": data.version,
            "description": data.description,
            "mount_files": data.mount_files,
        }
        result = await services_collection.insert_one(service_record)
        service_id = str(result.inserted_id)
        logger.info(f"Service record created with ID: {service_id}")

        # TODO: change this
        # find a convention for namespaces (namespace per DT Solution?)
        namespace = "default"

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
async def service_status():
    """Get the status of a DT service."""
    logger.info("Fetching service status")
    return {}


@router.get(
    "/{id}/output",
)
async def service_output():
    """Get the output of a DT service, if any."""
    logger.info("Fetching service output")
    return {}


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

        # Delete the service record from MongoDB
        services_collection = db.services
        result = await services_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Service not found in database")
        logger.info(f"Service record with ID {id} deleted from MongoDB")

        return {"message": "Service terminated successfully"}

    except ApiException as e:
        logger.error(f"Exception when deleting custom resource: {e}")
        raise HTTPException(
            status_code=e.status, detail=f"Exception when deleting custom resource: {e}"
        )

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
