from typing import TYPE_CHECKING

import pydantic as pyd
from typing_extensions import TypedDict

from .. import utils as general_utils
from .allocation_timeseries import allocation_timeseries
from .chart_datatypes import ChartData, MultiChartData
from .overall_lab_tat import overall_lab_tat
from .overall_tat import overall_tat
from .queue_length import q_length_means
from .tat_by_stage import tat_by_stage
from .tat_dist import tat_dist
from .utilization import utilisation_hourlies, utilisation_means
from .wip import wip_hourlies

if TYPE_CHECKING:
    from ..simulation.model import Model

# TODO: create confidence-interval versions of the below KPI functions


Progress = TypedDict("Progress", {"7": float, "10": float, "12": float, "21": float})
"""Returns the proportion of specimens completed within 7, 10, 12, and 21 days."""

LabProgress = TypedDict("LabProgress", {"3": float})
"""Returns the proportion of specimens with lab component completed within three days."""


class Report(pyd.BaseModel):
    """Dataclass for reporting a set of KPIs for passing to a frontend visualisation server.
    In the current implementation, this is https://github.com/lakeesiv/digital-twin"""

    overall_tat: float
    lab_tat: float
    progress: Progress
    lab_progress: LabProgress
    tat_by_stage: ChartData
    resource_allocation: dict[str, ChartData]  # ChartData for each resource
    wip_by_stage: MultiChartData
    utilization_by_resource: ChartData
    q_length_by_resource: ChartData
    hourly_utilization_by_resource: MultiChartData

    overall_tat_min: float | None = pyd.Field(default=None)
    overall_tat_max: float | None = pyd.Field(default=None)
    lab_tat_min: float | None = pyd.Field(default=None)
    lab_tat_max: float | None = pyd.Field(default=None)
    progress_min: Progress | None = pyd.Field(default=None)
    progress_max: Progress | None = pyd.Field(default=None)
    lab_progress_min: LabProgress | None = pyd.Field(default=None)
    lab_progress_max: LabProgress | None = pyd.Field(default=None)

    @staticmethod
    def from_model(mdl: "Model") -> "Report":
        """Produce a single dataclass for passing simulation results to a frontend server."""
        return __class__(
            overall_tat=overall_tat(mdl),
            lab_tat=overall_lab_tat(mdl),
            progress=dict(
                zip(
                    ["7", "10", "12", "21"], tat_dist(mdl, [7, 10, 12, 21]).TAT.tolist()
                )
            ),
            lab_progress=dict(zip(["3"], tat_dist(mdl, [3]).TAT_lab.tolist())),
            tat_by_stage=ChartData.from_pandas(tat_by_stage(mdl)),
            resource_allocation={
                res.name(): ChartData.from_pandas(allocation_timeseries(res))
                for res in general_utils.dc_values(mdl.resources)
            },
            wip_by_stage=MultiChartData.from_pandas(wip_hourlies(mdl)),
            utilization_by_resource=ChartData.from_pandas(utilisation_means(mdl)),
            q_length_by_resource=ChartData.from_pandas(q_length_means(mdl)),
            hourly_utilization_by_resource=MultiChartData.from_pandas(
                utilisation_hourlies(mdl)
            ),
        )
