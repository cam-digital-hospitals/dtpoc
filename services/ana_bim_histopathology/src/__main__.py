import json
import logging
import sys

import networkx as ntx

from . import models
from .conf import BIM_FILE, DEFAULT_RUNNER_SPEED, OUTPUT_FILE

if __name__ == "__main__":
    try:
        door_list = [f"d{n}" for n in range(1, 17)]
        extra_paths = [
            models.PathSegment(
                path=["d10", "d12"], duration_seconds=120.0, required_assets=["Lift"]
            ),
            models.PathSegment(
                path=["d11", "d13"], duration_seconds=45.0, required_assets=["Lift"]
            ),
        ]
        runner_speed = DEFAULT_RUNNER_SPEED

        logging.info("Received job with ID %s", "xyz")

        model = models.BimModel.from_ifc(BIM_FILE)
        g = models.logical_graph(
            model=model,
            door_list=door_list,
            extra_paths=extra_paths,
            runner_speed=runner_speed,
        )
        graph_data = ntx.node_link_data(g)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(graph_data, f)
    except Exception as e:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(e.__dict__, f)
            sys.exit(-1)
