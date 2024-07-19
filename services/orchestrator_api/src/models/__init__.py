import enum
from typing import Any, Optional, Self, Union

import pydantic as pyd


class ServiceType(enum.StrEnum):
    ANALYTICS = "ana"
    SIMULATION = "sim"

    @classmethod
    def list_values(cls) -> list[str]:
        return [e.value for e in cls]


class JobType(enum.StrEnum):
    PERSISTENT = "persistent"
    ONDEMAND = "ondemand"
    SCHEDULED = "scheduled"


class SimulationConfig(pyd.BaseModel):
    """Config for the simulation module type"""

    pass


class AnalyticsConfig(pyd.BaseModel):
    """Config for the analytics module type"""

    job_type: JobType = pyd.Field()
    """
    Type of the job:
      persistent => kubernetes Pod.
      ondemand => kubernetes Job.
      scheduled => kubernetes CronJob.
    """
    
    reps: Optional[int] = pyd.Field(
        default=None,
        examples=[
            3,
        ],
    )
    """Number of job completions required"""

    schedule: Optional[str] = pyd.Field(
        default=None,
        pattern=r"^((?:\*|[0-5]?[0-9](?:(?:-[0-5]?[0-9])|(?:,[0-5]?[0-9])+)?)(?:\/[0-9]+)?)\s+((?:\*|(?:1?[0-9]|2[0-3])(?:(?:-(?:1?[0-9]|2[0-3]))|(?:,(?:1?[0-9]|2[0-3]))+)?)(?:\/[0-9]+)?)\s+((?:\*|(?:[1-9]|[1-2][0-9]|3[0-1])(?:(?:-(?:[1-9]|[1-2][0-9]|3[0-1]))|(?:,(?:[1-9]|[1-2][0-9]|3[0-1]))+)?)(?:\/[0-9]+)?)\s+((?:\*|(?:[1-9]|1[0-2])(?:(?:-(?:[1-9]|1[0-2]))|(?:,(?:[1-9]|1[0-2]))+)?)(?:\/[0-9]+)?)\s+((?:\*|[0-7](?:-[0-7]|(?:,[0-7])+)?)(?:\/[0-9]+)?)$",
        examples=[
            "5 0 * 8 *",
            "0 22 * * 1-5",
        ],
    )
    """Cron schedule expression"""

    @pyd.model_validator(mode="after")
    def check_model_validity(self) -> Self:
        if self.job_type == JobType.SCHEDULED:
            assert (
                self.schedule is not None
            ), "Schedule must be provided for scheduled jobs"
        return self


class ServiceLaunchRequest(pyd.BaseModel):
    image: str = pyd.Field(
        examples=[
            "ghcr.io/cam-digital-hospitals/ana-hpath-sim"
        ],
    )
    """Docker image with the service logic"""

    version: str = pyd.Field(
        examples=[
            "latest",
        ],
    )
    """Version/Tag of the docker image to deploy"""

    description: str = pyd.Field(
        examples=[
            "An analytics module that uses the Histopathology BIM runner times to simulate sample flow and reports KPIs",
        ],
    )
    """Description of what the service does"""

    port: Optional[int] = pyd.Field(
        default=None,
        ge=1024,
        le=65535,
        examples=[8000],
    )
    """
    Port of the service to be exposed (using an ingress)

    Some DT components are not exposed. This field is ignored for those components.
    """

    env: Optional[dict[str, str]] = pyd.Field(
        default=None,
        examples=[
            {
                "INPUT_EXCEL_FILE": "/input/hpath_sim_input.xlsx",
                "OUTPUT_FOLDER": "/output",
            }
        ],
    )
    """A map of environment variables to be used for the service"""

    mount_files: Optional[dict[str, str]] = pyd.Field(
        default=None,
        examples=[
            {
                "668481b1af010b6fdc495b6c": "hpath_sim_input.xlsx",
            }
        ],
    )
    """A map of ids to the input files stored in the database and the path to mount"""

    ana: Union[AnalyticsConfig, None] = pyd.Field(
        title="Config for the analytics module type",
        default=None,
        examples=[
            {
                'job_type': 'ondemand'
            }
        ],
    )

    sim: Union[SimulationConfig, None] = pyd.Field(
        title="Config for the simulation module type",
        default=None,
        examples=[],
    )

    @pyd.model_validator(mode="before")
    @classmethod
    def verify_only_one_type(cls, data: Any) -> Any:
        if isinstance(data, dict):
            no_of_configs = sum(
                [
                    bool(data.get("ana", False)),
                    bool(data.get("sim", False)),
                ]
            )
            assert (
                no_of_configs == 1
            ), f"DT Service can only be of one type: {ServiceType.list_values()}"
        return data


class ServiceLaunchResponse(pyd.BaseModel):
    id: str
