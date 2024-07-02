from typing import TYPE_CHECKING

import pandas as pd

from .. import utils as general_utils
from .utils import extract_finalized_specimen_data

if TYPE_CHECKING:
    from ..simulation.model import Model


def tat_by_stage(mdl: "Model") -> pd.DataFrame:
    """Return a dataframe with the histopath stages as rows, and
    the mean turnaround time of each stage as its "mean (hours)" column."""
    specimen_data = extract_finalized_specimen_data(mdl)

    stages = [
        x.rsplit("_end", 1)[0] for x in specimen_data.columns if x.endswith("_end")
    ]
    df = pd.concat(
        [specimen_data[f"{x}_end"] - specimen_data[f"{x}_start"] for x in stages],
        axis="columns",
    )
    df.columns = stages

    ret = pd.DataFrame({"mean (hours)": df.mean()})
    ret.index = [wip.name() for wip in general_utils.dc_values(mdl.wips)][
        1:
    ]  # Remove 'Total' to match ret data
    return ret
