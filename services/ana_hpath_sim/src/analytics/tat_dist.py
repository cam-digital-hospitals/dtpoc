from typing import TYPE_CHECKING, Iterable

import numpy as np
import pandas as pd

from .utils import extract_finalized_specimen_data

if TYPE_CHECKING:
    from ..simulation.model import Model


def tat_dist(mdl: "Model", day_list: Iterable[int]) -> pd.DataFrame:
    """Return a dataframe showing the proportion of specimens
    completed within ``n`` days, for ``n`` in ``day_list``. Both
    overall and lab turnaround time are shown."""

    # Actually contains more data than just timestamps but we will ignore those columns
    timestamps = extract_finalized_specimen_data(mdl)

    # Extract TAT from data columns
    tat_total = timestamps["report_end"] - timestamps["reception_start"]
    tat_lab = timestamps["qc_end"] - timestamps["reception_start"]

    return pd.DataFrame(
        [
            {
                "days": days,
                "TAT": np.mean(tat_total <= days * 24),
                "TAT_lab": np.mean(tat_lab <= days * 24),
            }
            for days in day_list
        ]
    ).set_index("days")
