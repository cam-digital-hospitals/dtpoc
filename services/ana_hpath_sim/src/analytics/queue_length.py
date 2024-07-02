from typing import TYPE_CHECKING

import pandas as pd

from .. import utils as general_utils
from .utilization import utilisation_hourly

if TYPE_CHECKING:
    from salabim import Resource

    from ..simulation.model import Model


def q_length_means(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe showing the mean queue length of each resource."""
    ret = {
        r.name(): r.requesters().length.mean() / r.capacity.mean()
        for r in general_utils.dc_values(mdl.resources)
    }
    return pd.DataFrame({"mean": ret})


def q_length_hourly(res: "Resource") -> pd.DataFrame:
    """Return a dataframe showing the hourly mean queue length for a resource.
    Queue members can be specimen, block, slide, or batch tasks including delivery."""
    df = (
        pd.DataFrame(res.requesters().length.tx())
        .T.rename(columns={0: "t", 1: res.name()})
        .set_index("t")
    )
    df.index = pd.to_timedelta(df.index, unit="h")
    df1 = df.resample("h").mean()
    df1.index /= pd.Timedelta(1, unit="h")

    # handle hour intervals with no queue changes
    df2 = df.resample("h").ffill()
    df2.index /= pd.Timedelta(1, unit="h")
    return df1.fillna(df2)


def q_length_hourlies(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe showing the hourly mean queue length of each resource.
    Queue members can be specimen, block, slide, or batch tasks including delivery."""
    return pd.concat(
        [utilisation_hourly(res) for res in general_utils.dc_values(mdl.resources)],
        axis="columns",
    )
