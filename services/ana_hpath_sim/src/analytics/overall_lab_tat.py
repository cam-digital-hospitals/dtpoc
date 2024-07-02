from typing import TYPE_CHECKING

import pandas as pd

from .utils import extract_finalized_specimen_data

if TYPE_CHECKING:
    from ..simulation.model import Model


def overall_lab_tat(mdl: "Model") -> pd.DataFrame:
    """Overall mean turnaround time."""
    specimen_data = extract_finalized_specimen_data(mdl)
    # Extract TAT from data columns
    tat_lab = specimen_data["qc_end"] - specimen_data["reception_start"]
    return tat_lab.mean()
