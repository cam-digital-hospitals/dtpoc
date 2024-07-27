import logging
import os

from bson import ObjectId
import kopf
from kubernetes import client as k8s_client
from kubernetes.client import ApiException
from motor.core import AgnosticCollection
import requests

from orchestrator_operator.conf import (
    MAX_PARALLEL_JOB_RUNS,
    PROJECT_GROUP,
    VERSION,
    WATCH_CLIENT_TIMEOUT,
    WATCH_SERVER_TIMEOUT,
)
from orchestrator_operator.database import get_mongo_client


@kopf.on.login()
def login_fn(**kwargs):
    return kopf.login_via_client(**kwargs)


@kopf.on.startup()
def startup_tasks(settings: kopf.OperatorSettings, logger, **_):
    """Perform all necessary startup tasks here. Keep them lightweight and relevant
    as the other handlers won't be initialized until these tasks are complete"""
    logging.getLogger("aiohttp.access").setLevel(logging.WARN)
    logging.getLogger("httpx").setLevel(logging.WARN)
    # Running the operator as a standalone
    # https://kopf.readthedocs.io/en/stable/peering/?highlight=standalone#standalone-mode
    settings.peering.standalone = True
    settings.posting.level = logging.WARNING
    # settings.persistence.finalizer = f"operator.{oc_settings.PROJECT_GROUP}/finalizer"

    settings.watching.client_timeout = WATCH_CLIENT_TIMEOUT
    settings.watching.server_timeout = WATCH_SERVER_TIMEOUT

    # Disable k8s event logging
    settings.posting.enabled = False
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(
        prefix=PROJECT_GROUP
    )

def upload_file_to_endpoint(file_path, endpoint_url, logger):
    # logger.debug(f"opening file {file_path}")
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(endpoint_url, files=files)
        # logger.info(f"file upload response: {response}")
        if response.status_code == 200:
            logger.info(f"File {file_path} uploaded successfully.")
            return response.json().get('file_id')
        else:
            logger.info(f"Failed to upload file {file_path}. Status code: {response.status_code}, Response: {response.text}")
            return None

@kopf.timer(PROJECT_GROUP, VERSION, "analytics", interval=10.0)
async def check_output(spec: kopf.Spec, status: kopf.Status, name, namespace, logger: logging.Logger, **kwargs):
    job_type = spec.get('jobType')

    if job_type == "ondemand":
        # batch_api = k8s_client.BatchV1Api()
        # core_api = k8s_client.CoreV1Api()
        # Check job status
        # job = batch_api.read_namespaced_job(name=name, namespace=namespace)
        # if job.status.succeeded:
        #     logger.info(f"Job {name} succeeded with {job.status.succeeded} completions.")
        # else:
        #     logger.info(f"Job {name} status: {job.status}")
        
        # # Get a list of pods created by this job
        # pod_label_selector = f'job-name={name}'
        # pods = core_api.list_namespaced_pod(namespace=namespace, label_selector=pod_label_selector)
        # successful_pods = [pod.metadata.name for pod in pods.items if pod.status.phase == 'Succeeded']
        
        # logger.info(f"Successful pods for job {name}: {successful_pods}")
        
        mongo_client = get_mongo_client()
        # Get the "services" collection in the "orchestrator" database
        services_collection: AgnosticCollection = mongo_client.orchestrator.services
        
        service = await services_collection.find_one({"_id": ObjectId(name)})
        file_ids = service.get('output_files')
        
        if not file_ids:
            file_ids = {}
        
        for file in os.listdir('/data'):
            filepath = os.path.join("/data", file)
            if name in filepath:
                logger.info(f"uploading file: {filepath}")
                endpoint_url = "http://orchestrator-api-svc.default.svc.cluster.local/api/orchestrator/v1alpha1/files/upload"
                file_id = upload_file_to_endpoint(filepath, endpoint_url, logger)
                if file_id:
                    file_ids.update({file_id: file})
                    os.remove(filepath)
        
        await services_collection.update_one({"_id": ObjectId(name)}, {"$set": {"output_files": file_ids}})

@kopf.on.create(PROJECT_GROUP, VERSION, "analytics")
@kopf.on.resume(PROJECT_GROUP, VERSION, "analytics")
async def analytics_handler(
    spec: kopf.Spec,
    name: str,
    namespace: str,
    uid: str,
    logger: logging.Logger,
    status: kopf.Status,
    **kwargs,
):
    job_type = spec.get("jobType")
    image = spec.get("image")
    port = spec.get("port")
    schedule = spec.get("schedule")
    reps = spec.get("reps")
    env_vars = spec.get("env", {})

    owner_reference = k8s_client.V1OwnerReference(
        api_version=f"{PROJECT_GROUP}/{VERSION}",
        kind="Analytics",
        name=name,
        uid=uid,
        controller=True,
        block_owner_deletion=True,
    )

    mongo_client = get_mongo_client()

    # Get the "services" collection in the "orchestrator" database
    services_collection: AgnosticCollection = mongo_client.orchestrator.services

    result = await services_collection.find_one({"_id": ObjectId(name)})

    if not result:
        raise kopf.TemporaryError(f"Service id: {name} not found in database!")

    # Files to be mounted to the container
    mount_files = result["mount_files"] if result["mount_files"] else {}

    container_spec = k8s_client.V1Container(
        name="main",
        image=image,
        image_pull_policy="IfNotPresent",
        env=[
            # Improvement: create access-restricted user credentials
            # that gives access to only the table/collections the service
            # is authorized to access.
            k8s_client.V1EnvVar(
                name="MONGO_HOST",
                value="mongodb.default.svc.cluster.local",
            ),
            k8s_client.V1EnvVar(name="MONGO_PORT", value="27017"),
            k8s_client.V1EnvVar(name="MONGO_USER", value="root"),
            k8s_client.V1EnvVar(name="MONGO_PASSWORD", value="password"),
            k8s_client.V1EnvVar(
                name="RUN_ID",
                value_from=k8s_client.V1EnvVarSource(
                    field_ref=k8s_client.V1ObjectFieldSelector(field_path="metadata.name")
                )
            ),
            *[
                k8s_client.V1EnvVar(name=key, value=value)
                for key, value in env_vars.items()
            ],
        ],
        volume_mounts=(
            [
                k8s_client.V1VolumeMount(name="shared-data", mount_path="/input"),
                k8s_client.V1VolumeMount(name="output-data", mount_path="/output"),
            ]
            if job_type == "ondemand" or job_type == "scheduled"
            else []
        ),
    )

    if job_type == "ondemand":
        batch_api = k8s_client.BatchV1Api()
        try:
            existing_job = batch_api.read_namespaced_job(name=name, namespace=namespace)
            print(f"Job {name} already exists.")
        except ApiException as e:
            if e.status == 404:
                # Job does not exist, proceed to create it
                batch_api.create_namespaced_job(
                    namespace=namespace,
                    body=k8s_client.V1Job(
                        api_version="batch/v1",
                        kind="Job",
                        metadata=k8s_client.V1ObjectMeta(
                            name=name, owner_references=[owner_reference]
                        ),
                        spec=k8s_client.V1JobSpec(
                            parallelism=MAX_PARALLEL_JOB_RUNS,
                            completions=reps,
                            template=k8s_client.V1PodTemplateSpec(
                                spec=k8s_client.V1PodSpec(
                                    init_containers=[
                                        # Init container that prepares input files for the analytics module
                                        # Improvement: a dedicated service the can handle failures and
                                        # directly accesses the DS for files.
                                        k8s_client.V1Container(
                                            name="init-download-files",
                                            image="curlimages/curl",
                                            command=["/bin/sh", "-c"],
                                            args=[
                                                " && ".join(
                                                    [
                                                        f"curl -o /input/{file_path} http://orchestrator-api-svc.default.svc.cluster.local/files/{file_id}"
                                                        for file_id, file_path in mount_files.items()
                                                    ]
                                                )
                                            ],
                                            volume_mounts=[
                                                k8s_client.V1VolumeMount(
                                                    name="shared-data", mount_path="/input"
                                                )
                                            ],
                                        )
                                    ],
                                    containers=[
                                        container_spec,
                                    ],
                                    restart_policy="Never",
                                    volumes=[
                                        k8s_client.V1Volume(
                                            name="shared-data",
                                            empty_dir=k8s_client.V1EmptyDirVolumeSource(),
                                        ),
                                        k8s_client.V1Volume(
                                            name="output-data",
                                            persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(
                                                claim_name="orchestrator-pvc"
                                            ),
                                        ),
                                    ],
                                )
                            )
                        ),
                    ),
                )
            else:
                raise kopf.TemporaryError(f"Unknown error: {e}")

        return {"job_creation": True}

    elif job_type == "persistent":
        apps_api = k8s_client.AppsV1Api()
        apps_api.create_namespaced_deployment(
            namespace=namespace,
            body=k8s_client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=k8s_client.V1ObjectMeta(
                    name=name, namespace=namespace, owner_references=[owner_reference]
                ),
                spec=k8s_client.V1DeploymentSpec(
                    template=k8s_client.V1PodTemplateSpec(
                        metadata=k8s_client.V1ObjectMeta(labels={"app": name}),
                        spec=k8s_client.V1PodSpec(
                            containers=[container_spec],
                        ),
                    )
                ),
            ),
        )

        if port:
            core_api = k8s_client.CoreV1Api()
            core_api.create_namespaced_service(
                namespace=namespace,
                body=k8s_client.V1Service(
                    api_version="v1",
                    kind="Service",
                    metadata=k8s_client.V1ObjectMeta(
                        name=name,
                        namespace=namespace,
                        owner_references=[owner_reference],
                    ),
                    spec=k8s_client.V1ServiceSpec(
                        selector={"app": name},
                        ports=[k8s_client.V1ServicePort(port=port, target_port=port)],
                    ),
                ),
            )

            networking_api = k8s_client.NetworkingV1Api()
            networking_api.create_namespaced_ingress(
                namespace=namespace,
                body=k8s_client.V1Ingress(
                    api_version="networking.k8s.io/v1",
                    kind="Ingress",
                    metadata=k8s_client.V1ObjectMeta(
                        name=name,
                        namespace=namespace,
                        owner_references=[owner_reference],
                    ),
                    spec=k8s_client.V1IngressSpec(
                        rules=[
                            k8s_client.V1IngressRule(
                                http=k8s_client.V1HTTPIngressRuleValue(
                                    paths=[
                                        k8s_client.V1HTTPIngressPath(
                                            path="/",
                                            path_type="Prefix",
                                            backend=k8s_client.V1IngressBackend(
                                                service=k8s_client.V1IngressServiceBackend(
                                                    name=name,
                                                    port=k8s_client.V1ServiceBackendPort(
                                                        number=port
                                                    ),
                                                )
                                            ),
                                        )
                                    ]
                                ),
                            )
                        ]
                    ),
                ),
            )

        return {"job_creation": True}

    else:
        raise kopf.PermanentError("Unsupported job_type")
