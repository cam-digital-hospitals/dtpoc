from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from salabim import Resource


def allocation_timeseries(res: "Resource") -> pd.DataFrame:
    """Return a dataframe showing the allocation level of a resource."""
    df = (
        pd.DataFrame(res.capacity.tx())
        .T.rename(columns={0: "t", 1: res.name()})
        .set_index("t")
    )
    # Duplicates can happen as the final allocation change may be at the
    # simulation end time.  Remove these.
    return df.groupby("t").tail(1)
