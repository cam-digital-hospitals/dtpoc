import logging

from bson import ObjectId
import kopf
from kubernetes import client as k8s_client
from motor.core import AgnosticCollection

from orchestrator_operator.conf import (
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


@kopf.on.create(PROJECT_GROUP, VERSION, "analytics")
@kopf.on.resume(PROJECT_GROUP, VERSION, "analytics")
async def analytics_handler(
    spec: kopf.Spec,
    name: str,
    namespace: str,
    uid: str,
    logger: logging.Logger,
    **kwargs,
):
    job_type = spec.get("jobType")
    image = spec.get("image")
    port = spec.get("port")
    schedule = spec.get("schedule")
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

    batch_api = k8s_client.BatchV1Api()

    if job_type == "ondemand":
        job = k8s_client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=k8s_client.V1ObjectMeta(
                name=name, owner_references=[owner_reference]
            ),
            spec=k8s_client.V1JobSpec(
                template=k8s_client.V1PodTemplateSpec(
                    spec=k8s_client.V1PodSpec(
                        init_containers=[
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
                            k8s_client.V1Container(
                                name="main",
                                image=image,
                                image_pull_policy="IfNotPresent",
                                env=[
                                    k8s_client.V1EnvVar(
                                        name="MONGO_HOST",
                                        value="mongodb.default.svc.cluster.local",
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="MONGO_PORT", value="27017"
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="MONGO_USER", value="root"
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="MONGO_PASSWORD", value="password"
                                    ),
                                    *[
                                        k8s_client.V1EnvVar(name=key, value=value)
                                        for key, value in env_vars.items()
                                    ],
                                ],
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="shared-data", mount_path="/input"
                                    )
                                ],
                            )
                        ],
                        restart_policy="Never",
                        volumes=[
                            k8s_client.V1Volume(
                                name="shared-data",
                                empty_dir=k8s_client.V1EmptyDirVolumeSource(),
                            ),
                        ],
                    )
                )
            ),
        )

        batch_api.create_namespaced_job(namespace=namespace, body=job)

        return {"job-name": job.metadata.name}

    # if job_type == "persistent":
    #     create_deployment(
    #         name, namespace, image, port, env_vars, owner_reference, k8s_api
    #     )
    #     create_service(name, namespace, port, owner_reference, core_api)
    #     create_ingress(name, namespace, port, owner_reference, networking_api)
    # elif job_type == "scheduled":
    #     create_cronjob(
    #         name, namespace, image, schedule, env_vars, owner_reference, batch_api
    #     )
    # else:
    #     await create_job(name, namespace, image, env_vars, owner_reference, batch_api)


# async def create_job(
#     name, namespace, image, env_vars, owner_reference, batch_api: k8s_client.BatchV1Api
# ):
#     mongo_client = get_mongo_client()
#     # Get the "services" collection in the "orchestrator" database
#     services_collection: AgnosticCollection = mongo_client.orchestrator.services

#     result = await services_collection.find_one({"_id": ObjectId(name)})
#     # print(result)

#     if not result:
#         raise Exception(f"Service with name {name} not found")

#     env_list = [
#         k8s_client.V1EnvVar(
#             name="MONGO_HOST", value="mongodb.default.svc.cluster.local"
#         ),
#         k8s_client.V1EnvVar(name="MONGO_PORT", value="27017"),
#         k8s_client.V1EnvVar(name="MONGO_USER", value="root"),
#         k8s_client.V1EnvVar(name="MONGO_PASSWORD", value="password"),
#         *[
#             k8s_client.V1EnvVar(name=key, value=value)
#             for key, value in env_vars.items()
#         ],
#     ]

#     # Volumes for sharing data between init container and main container
#     volumes = [
#         k8s_client.V1Volume(
#             name="shared-data", empty_dir=k8s_client.V1EmptyDirVolumeSource()
#         ),
#         k8s_client.V1Volume(
#             name="output-data", empty_dir=k8s_client.V1EmptyDirVolumeSource()
#         ),
#     ]

#     mount_files = result["mount_files"] if result["mount_files"] else {}

#     # Init container for downloading files
#     # init_container =

#     container = k8s_client.V1Container(
#         name="job",
#         image=image,
#         env=env_list,
#         image_pull_policy="IfNotPresent",
#         volume_mounts=[
#             k8s_client.V1VolumeMount(name="shared-data", mount_path="/input"),
#             k8s_client.V1VolumeMount(name="output-data", mount_path="/output"),
#         ],
#     )

#     output_monitor = k8s_client.V1Container(
#         name="output-monitor",
#         image="appropriate/curl",
#         command=["/bin/sh", "-c"],
#         args=["tail -f /dev/null"],
#         volume_mounts=[
#             k8s_client.V1VolumeMount(name="output-data", mount_path="/output"),
#         ],
#     )

#     spec = k8s_client.V1PodSpec(
#         containers=[
#             container,
#             output_monitor,
#         ],
#         init_containers=[init_container] if mount_files else [],
#         restart_policy="OnFailure",
#         volumes=volumes,
#     )
#     template = k8s_client.V1PodTemplateSpec(
#         metadata=k8s_client.V1ObjectMeta(labels={"app": name}), spec=spec
#     )

#     job_spec = k8s_client.V1JobSpec(template=template)

#     job = k8s_client.V1Job(
#         api_version="batch/v1",
#         kind="Job",
#         metadata=k8s_client.V1ObjectMeta(
#             name=name, namespace=namespace, owner_references=[owner_reference]
#         ),
#         spec=job_spec,
#     )

#     batch_api.create_namespaced_job(namespace=namespace, body=job)


# def create_deployment(name, namespace, image, port, env_vars, owner_reference, k8s_api):
#     env_list = [
#         k8s_client.V1EnvVar(
#             name="MONGO_HOST", value="mongodb.default.svc.cluster.local"
#         ),
#         k8s_client.V1EnvVar(name="MONGO_PORT", value="27017"),
#         k8s_client.V1EnvVar(name="MONGO_USER", value="root"),
#         k8s_client.V1EnvVar(name="MONGO_PASSWORD", value="password"),
#         *[
#             k8s_client.V1EnvVar(name=key, value=value)
#             for key, value in env_vars.items()
#         ],
#     ]

#     container = k8s_client.V1Container(
#         name=name,
#         image=image,
#         ports=[k8s_client.V1ContainerPort(container_port=port)] if port else [],
#         env=env_list,
#     )

#     spec = k8s_client.V1PodSpec(containers=[container])
#     template = k8s_client.V1PodTemplateSpec(
#         metadata=k8s_client.V1ObjectMeta(labels={"app": name}), spec=spec
#     )

#     deployment_spec = k8s_client.V1DeploymentSpec(
#         replicas=1, template=template, selector={"matchLabels": {"app": name}}
#     )

#     deployment = k8s_client.V1Deployment(
#         api_version="apps/v1",
#         kind="Deployment",
#         metadata=k8s_client.V1ObjectMeta(
#             name=name, namespace=namespace, owner_references=[owner_reference]
#         ),
#         spec=deployment_spec,
#     )

#     k8s_api.create_namespaced_deployment(namespace=namespace, body=deployment)


# def create_service(name, namespace, port, owner_reference, core_api):
#     if not port:
#         return

#     service_spec = k8s_client.V1ServiceSpec(
#         selector={"app": name},
#         ports=[k8s_client.V1ServicePort(port=port, target_port=port)],
#     )

#     service = k8s_client.V1Service(
#         api_version="v1",
#         kind="Service",
#         metadata=k8s_client.V1ObjectMeta(
#             name=name, namespace=namespace, owner_references=[owner_reference]
#         ),
#         spec=service_spec,
#     )

#     core_api.create_namespaced_service(namespace=namespace, body=service)


# def create_ingress(name, namespace, port, owner_reference, networking_api):
#     if not port:
#         return

#     ingress_backend = k8s_client.V1IngressBackend(
#         service=k8s_client.V1IngressServiceBackend(
#             name=name, port=k8s_client.V1ServiceBackendPort(number=port)
#         )
#     )

#     ingress_rule = k8s_client.V1IngressRule(
#         http=k8s_client.V1HTTPIngressRuleValue(
#             paths=[
#                 k8s_client.V1HTTPIngressPath(
#                     path="/", path_type="Prefix", backend=ingress_backend
#                 )
#             ]
#         ),
#     )

#     ingress_spec = k8s_client.V1IngressSpec(rules=[ingress_rule])

#     ingress = k8s_client.V1Ingress(
#         api_version="networking.k8s.io/v1",
#         kind="Ingress",
#         metadata=k8s_client.V1ObjectMeta(
#             name=name, namespace=namespace, owner_references=[owner_reference]
#         ),
#         spec=ingress_spec,
#     )

#     networking_api.create_namespaced_ingress(namespace=namespace, body=ingress)


# def create_cronjob(
#     name, namespace, image, schedule, env_vars, owner_reference, batch_api
# ):
#     env_list = [
#         k8s_client.V1EnvVar(name=key, value=value) for key, value in env_vars.items()
#     ]

#     container = k8s_client.V1Container(name=name, image=image, env=env_list)

#     spec = k8s_client.V1PodSpec(containers=[container], restart_policy="OnFailure")
#     template = k8s_client.V1PodTemplateSpec(
#         metadata=k8s_client.V1ObjectMeta(labels={"app": name}), spec=spec
#     )

#     cronjob_spec = k8s_client.V1CronJobSpec(
#         schedule=schedule,
#         job_template=k8s_client.V1JobTemplateSpec(
#             spec=k8s_client.V1JobSpec(template=template)
#         ),
#     )

#     cronjob = k8s_client.V1CronJob(
#         api_version="batch/v1",
#         kind="CronJob",
#         metadata=k8s_client.V1ObjectMeta(
#             name=name, namespace=namespace, owner_references=[owner_reference]
#         ),
#         spec=cronjob_spec,
#     )

#     batch_api.create_namespaced_cron_job(namespace=namespace, body=cronjob)
