from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..simulation.model import Model


def extract_finalized_specimen_data(model: "Model") -> pd.DataFrame:
    """
    Extracts and formats data for specimens that have completed their processing cycle.

    This function filters out initial or bootstrap specimens and retains only those
    specimens that have a recorded 'report_end' timestamp, indicating completion.
    The index of the returned DataFrame is set to a simplified numeric identifier
    extracted from the original specimen identifier.

    Args:
        mdl (Model): An instance of the Model class containing specimen data.

    Returns:
        pd.DataFrame: A DataFrame where each row corresponds to a completed specimen,
                      indexed by a simplified numeric identifier of the specimen.
    """
    specimen_data = pd.DataFrame.from_dict(
        {
            # Only keep non-bootstrap specimens that have completed service
            k: v
            for k, v in model.specimen_data.items()
            if "init" not in k and "report_end" in v
        },
        orient="index",
    )

    # specimen.123 -> 123
    specimen_data.index = [int(idx.rsplit(".", 1)[1]) for idx in specimen_data.index]
    return specimen_data
