from typing import TYPE_CHECKING

import pandas as pd

from .. import utils as general_utils

if TYPE_CHECKING:
    from salabim import Monitor, Resource

    from ..simulation.model import Model


def wip_hourly(wip: "Monitor") -> pd.DataFrame:
    """Return a dataframe showing the hourly mean WIP
    of a histopath stage."""
    df = pd.DataFrame(wip.tx()).T.rename(columns={0: "t", 1: wip.name()}).set_index("t")
    df.index = pd.to_timedelta(df.index, "h")

    df1 = df.resample("h").mean()
    df1.index /= pd.Timedelta(1, unit="h")

    # handle hour intervals with no WIP changes
    df2 = df.resample("h").ffill()
    df2.index /= pd.Timedelta(1, unit="h")
    return df1.fillna(df2)


def wip_hourlies(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe showing the hourly mean WIP
    for each stage in the histopathology process."""
    return pd.concat(
        [wip_hourly(wip) for wip in general_utils.dc_values(mdl.wips)], axis="columns"
    )


def wip_summary(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe with the histopath stages as rows, and
    the mean WIP of each stage as its "mean" column."""
    df = pd.DataFrame(
        {wip.name(): [wip.mean()] for wip in general_utils.dc_values(mdl.wips)}
    )
    df.index = ["mean"]
    return df.T
