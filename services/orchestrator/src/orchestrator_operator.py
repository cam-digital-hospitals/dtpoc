import logging

import kopf
from kubernetes import client
from kubernetes.client import ApiException

from .conf import PROJECT_GROUP, WATCH_CLIENT_TIMEOUT, WATCH_SERVER_TIMEOUT


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
