import pandas as pd
from fastapi import FastAPI

from .conf import TIMEZONE, VERSION

app = FastAPI(
    root_path=f"/api/ana-asset-outage/{VERSION}",
)


class OutageList(list):
    """A list of outages; returned by the function `get_outages`."""

    def to_df(self: list) -> pd.DataFrame:
        """Convert to a Pandas dataframe."""
        df = pd.DataFrame(self)
        df.start = to_localtime(df.start)
        df.end = to_localtime(df.end)
        df.updated = to_localtime(df.updated)
        df["interval"] = pd.arrays.IntervalArray.from_arrays(
            df.start, df.end, closed="both"
        )
        return df


def to_localtime(ts: pd.Series, fl: str = None) -> pd.Series:
    """Convert UNIX timestamps (s from 1970-01-01) to localtime."""
    ret = pd.to_datetime(ts, unit="s", origin="unix", utc=True)
    if fl is not None:
        ret = ret.dt.floor(fl)
    return ret.dt.tz_convert(TIMEZONE)
