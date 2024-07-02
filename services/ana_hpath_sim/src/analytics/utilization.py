from typing import TYPE_CHECKING

import pandas as pd
import salabim as sim

from .. import utils as general_utils

if TYPE_CHECKING:
    from ..simulation.model import Model


def utilisation_hourly(res: sim.Resource) -> pd.DataFrame:
    """Return a dataframe showing the hourly mean utilisation of a resource."""
    df = (
        pd.DataFrame(res.claimed_quantity.tx())
        .T.rename(columns={0: "t", 1: res.name()})
        .set_index("t")
    )
    df.index = pd.to_timedelta(df.index, unit="h")
    df1 = df.resample("h").mean()
    df1.index /= pd.Timedelta(1, unit="h")

    # handle hour intervals with no utilisation changes
    df2 = df.resample("h").ffill()
    df2.index /= pd.Timedelta(1, unit="h")
    return df1.fillna(df2)


def utilisation_hourlies(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe showing the hourly mean utilisation of each resource."""
    return pd.concat(
        [utilisation_hourly(res) for res in general_utils.dc_values(mdl.resources)],
        axis="columns",
    )


def utilisation_means(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe showing the mean utilisation of each resource."""
    ret = {
        r.name(): r.claimed_quantity.mean() / r.capacity.mean()
        for r in general_utils.dc_values(mdl.resources)
    }
    return pd.DataFrame({"mean": ret})
