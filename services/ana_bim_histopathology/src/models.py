from dataclasses import dataclass
from enum import StrEnum
from functools import reduce
from itertools import islice
from os import PathLike
from tempfile import NamedTemporaryFile
from typing import Self, Sequence

import ifcopenshell as ifc
import ifcopenshell.geom as ifc_geom
import ifcopenshell.util.shape as ifc_shape
import natsort
import networkx as ntx
import numpy as np
import pandas as pd
import pydantic as pyd
import shapely as shp

from .conf import DEFAULT_GRID_SIZE, DEFAULT_RUNNER_SPEED, settings


class _BimDataDoors(pyd.BaseModel):
    door_name: Sequence[str]
    floor: Sequence[str]
    x0: Sequence[float]
    x1: Sequence[float]
    y0: Sequence[float]
    y1: Sequence[float]
    z0: Sequence[float]


class _BimDataWalls(pyd.BaseModel):
    wall_name: Sequence[str]
    floor: Sequence[str]
    x0: Sequence[float]
    x1: Sequence[float]
    y0: Sequence[float]
    y1: Sequence[float]
    z0: Sequence[float]


class BimData(pyd.BaseModel):
    """Pydantic dataclass representation of a BimModel's data."""

    elevations: dict[str, float]
    doors: _BimDataDoors
    walls: _BimDataWalls

    @classmethod
    def from_obj(cls, x: "BimModel") -> Self:
        """Extract a BimData object from an BimModel instance."""
        return cls(
            elevations=x.elevations,
            doors=x.doors.to_dict(orient="list"),
            walls=x.walls.to_dict(orient="list"),
        )

    def to_obj(self) -> "BimModel":
        """Construct a BimModel from a BimData object."""
        return BimModel(
            elevations=self.elevations,
            doors=pd.DataFrame.from_dict(self.doors.model_dump(), orient="columns"),
            walls=pd.DataFrame.from_dict(self.walls.model_dump(), orient="columns"),
        )


@dataclass
class BimModel:
    """Representation of the histopathology lab's BIM data."""

    elevations: dict[str, float]
    """Elevation of each building storey, in metres."""

    doors: pd.DataFrame
    """Dataframe of door coordinate data."""

    walls: pd.DataFrame
    """Dataframe of wall coordinate data."""

    @classmethod
    def from_bytes(cls, model_bytes: bytes) -> Self:
        """Parse an Industry Foundation Classes (.ifc) representation of the
        histopathology lab, from a byte string."""
        with NamedTemporaryFile(delete_on_close=False) as fp:
            fp.write(model_bytes)
            fp.close()
            return cls.from_ifc(fp.name)

    @classmethod
    def from_ifc(cls, path: PathLike) -> Self:
        """Parse an Industry Foundation Classes (.ifc) representation of the
        histopathology lab, from a file."""
        ifc_file = ifc.open(path)

        # Get the list of elevations for each Storey in the IFC file.
        # Our IFC file is known to express elevation in mm, convert to m.
        elevations: dict[str, float] = reduce(
            lambda d1, d2: d1 | d2,
            map(
                lambda s: {s.Name: s.Elevation / 1000.0},
                ifc_file.by_type("ifcBuildingStorey"),
            ),
        )

        # Get the name of an IFC object; works for walls and doors
        # in the current IFC file.
        def get_level_name(obj: ifc.entity_instance) -> str:
            return obj.ContainedInStructure[0].RelatingStructure.Name

        # Get the bounding box of an IFC object; for our IFC file,
        # all walls and doors are aligned to the xyz axes.
        def get_coords(obj: ifc.entity_instance) -> dict[str, float]:
            shape = ifc_geom.create_shape(settings, obj)
            grouped_verts = ifc_shape.get_vertices(shape.geometry)
            return {
                "x0": min(map(lambda xyz: xyz[0], grouped_verts)),
                "y0": min(map(lambda xyz: xyz[1], grouped_verts)),
                "z0": min(map(lambda xyz: xyz[2], grouped_verts)),
                "x1": max(map(lambda xyz: xyz[0], grouped_verts)),
                "y1": max(map(lambda xyz: xyz[1], grouped_verts)),
                # 'z1': max(map(lambda xyz: xyz[2], grouped_verts))
            }

        # Extract door data
        doors = ifc_file.by_type("IfcDoor")
        doors_coords = [get_coords(door) for door in doors]
        doors_df = (
            pd.DataFrame(
                {
                    "door_name": [door.Name for door in doors],
                    "floor": [get_level_name(door) for door in doors],
                    "x0": [box["x0"] for box in doors_coords],
                    "x1": [box["x1"] for box in doors_coords],
                    "y0": [box["y0"] for box in doors_coords],
                    "y1": [box["y1"] for box in doors_coords],
                    "z0": [box["z0"] for box in doors_coords],
                    # 'z1': [box['z1'] for box in doors_coords]
                }
            )
            .sort_values(by="door_name", key=natsort.natsort_keygen())
            .reset_index(drop=True)
        )

        # Extract wall data
        walls = ifc_file.by_type("IfcWall")
        wall_coords = [get_coords(wall) for wall in walls]
        walls_df = pd.DataFrame(
            {
                "wall_name": [wall.Name for wall in walls],
                "floor": [get_level_name(wall) for wall in walls],
                "x0": [box["x0"] for box in wall_coords],
                "x1": [box["x1"] for box in wall_coords],
                "y0": [box["y0"] for box in wall_coords],
                "y1": [box["y1"] for box in wall_coords],
                "z0": [box["z0"] for box in wall_coords],
                # 'z1': [box['z1'] for box in wall_coords]
            }
        )

        return cls(elevations=elevations, doors=doors_df, walls=walls_df)


class BoxType(StrEnum):
    """Denotes whether a grid square is a source/target door, a wall, or empty space."""

    OK_DOOR = "ok_door"
    WALL = "wall"
    EMPTY = "empty"


@dataclass
class ShapelyModel:
    """Shapely representation of a floor in the histopathology lab.
    All doors and walls are represented as `shapely.Polygon` instances.
    """

    wall_shapes: list[shp.Polygon]
    door_shapes: dict[str, shp.Polygon]

    @dataclass
    class _Bounds:
        x_min: float
        x_max: float
        y_min: float
        y_max: float

    bounds: "ShapelyModel._Bounds"

    def __init__(
        self, bim_model: BimModel, level: str, include_doors: Sequence[str]
    ) -> None:
        """Construct a ShapelyModel from a level of a BimModel, including only doors of interest.

        Args:
            bim_model (BimModel): The BIM model to construct the `ShapelyModel` from.
            level (str): The level to model, e.g. `"Level 3 First Floor"`.
            include_doors (Sequence[str]): The doors to include in the model, e.g. `['d1', 'd2']`.
        """
        doors = bim_model.doors.loc[bim_model.doors.door_name.isin(include_doors)]

        wall_shapes = [
            shp.box(wall.x0, wall.y0, wall.x1, wall.y1, ccw=False)
            for wall in bim_model.walls.loc[bim_model.walls.floor == level].itertuples()
        ]

        door_shapes = {
            door.door_name: shp.box(door.x0, door.y0, door.x1, door.y1, ccw=False)
            for door in doors.loc[doors.floor == level].itertuples()
        }

        x_min = bim_model.walls.loc[bim_model.walls.floor == level].x0.min()
        x_max = bim_model.walls.loc[bim_model.walls.floor == level].x1.max()
        y_min = bim_model.walls.loc[bim_model.walls.floor == level].y0.min()
        y_max = bim_model.walls.loc[bim_model.walls.floor == level].y1.max()

        for s in wall_shapes:
            shp.prepare(s)
        for s in door_shapes.values():
            shp.prepare(s)

        self.wall_shapes = wall_shapes
        self.door_shapes = door_shapes
        self.bounds = ShapelyModel._Bounds(
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max
        )

    def is_valid_box(
        self, box: shp.Polygon, ok_doors: Sequence[str]
    ) -> tuple[bool, BoxType]:
        """Determines if `box` intersects with a wall or door except for `ok_doors`.
        `ok_doors` will typically be the source and destination doors of a shortest-path algorithm.

        Args:
            box: The box to check against the current model.
            ok_doors: A list of doors to ignore when checking for intersections.
        """

        # Since all doors are within walls, we only need to check the
        # ok_doors as special cases

        ok_door_shapes = [self.door_shapes[x] for x in ok_doors]
        shp.prepare(box)
        if any(box.intersects(ok_door_shapes)):
            # Intersects with door in ok_doors
            return True, BoxType.OK_DOOR
        if any(box.intersects(self.wall_shapes)):
            # Intersects with wall
            return False, BoxType.WALL
        return True, BoxType.EMPTY

    def shortest_path(
        self, from_door: str, to_door: str, grid_size=DEFAULT_GRID_SIZE
    ) -> tuple[float, ntx.Graph]:
        """Find the shortest path between two doors in the model.
        Movement is allowed in the four cardinal directions and diagonally within a
        complete rectangle.

        Args:
            from_door:
                Starting door on the path.
            to_door:
                Destination door on the path.
            grid_size:
                Grid size for pathfinding algorithm, in metres. Defaults to
                DEFAULT_GRID_SIZE`.

        Raises:
            networkx.NetworkXNoPath:
                If no path exists between `from_door` and `to_door` without
                passing through a wall or another door.
        """
        n_x = len(np.arange(self.bounds.x_min, self.bounds.x_max, grid_size))
        n_y = len(np.arange(self.bounds.y_min, self.bounds.y_max, grid_size))

        # Create base grid, assigning 'box' and 'pos' attributes
        # to each node
        grid = ntx.grid_2d_graph(n_x, n_y)
        for i, j in grid.nodes:
            x0 = self.bounds.x_min + i * grid_size
            y0 = self.bounds.y_min + j * grid_size
            grid.nodes[(i, j)]["box"] = shp.box(
                x0, y0, x0 + grid_size, y0 + grid_size, ccw=False
            )
            shp.prepare(grid.nodes[(i, j)]["box"])
            centroid = grid.nodes[(i, j)]["box"].centroid
            grid.nodes[(i, j)]["pos"] = (centroid.x, centroid.y)

        # Select valid nodes for subgraph
        selected_nodes = [
            n
            for n, v in grid.nodes(data=True)
            if self.is_valid_box(v["box"], ok_doors=[from_door, to_door])[0]
        ]
        grid2 = ntx.Graph(grid.subgraph(selected_nodes))

        # Add diagonals to grid2 within each complete "box" of 4 edges
        for _, _, v in grid2.edges(data=True):
            v["weight"] = 1.0

        for x, y in grid2.nodes:
            # northeast direction
            if (
                (x + 1, y) in grid2.nodes
                and (x, y + 1) in grid2.nodes
                and (x + 1, y + 1) in grid2.nodes
            ):
                grid2.add_edge((x, y), (x + 1, y + 1), weight=2**0.5)

            # southeast direction
            if (
                (x + 1, y) in grid2.nodes
                and (x, y - 1) in grid2.nodes
                and (x + 1, y - 1) in grid2.nodes
            ):
                grid2.add_edge((x, y), (x + 1, y - 1), weight=2**0.5)

        # Get node indexes for from_door and to_door
        from_node = [
            n
            for n, v in grid.nodes(data=True)
            if v["box"].intersects(self.door_shapes[from_door].centroid)
        ][0]
        to_node = [
            n
            for n, v in grid.nodes(data=True)
            if v["box"].intersects(self.door_shapes[to_door].centroid)
        ][0]

        path_nodes = ntx.shortest_path(grid2, from_node, to_node, weight="weight")
        path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
        path_graph = ntx.Graph()
        for i, n in enumerate(path_nodes):
            path_graph.add_node(i, pos=grid2.nodes(data=True)[n]["pos"])
        for i, e in enumerate(path_edges):
            path_graph.add_edge(i, i + 1, weight=grid2.edges[e]["weight"])

        path_length = (
            ntx.shortest_path_length(grid2, from_node, to_node, weight="weight")
            * grid_size
        )

        return path_length, path_graph

    def logical_graph(self, speed: float = DEFAULT_RUNNER_SPEED) -> ntx.Graph:
        """Construct a logical graph representation of the floor model,
        with nodes representing doors and edge weights representing travel
        times in seconds.

        Args:
            speed: Runner speed in m/s.

        Returns:
            The logical graph for the given floor model.
        """
        graph = ntx.Graph()
        keys = list(self.door_shapes.keys())
        graph.add_nodes_from(keys)
        for i, k1 in enumerate(keys):
            for _, k2 in islice(enumerate(keys), i + 1, None):
                try:
                    path_len, _ = self.shortest_path(k1, k2)
                    graph.add_edge(
                        k1, k2, weight=path_len / speed
                    )  # weight = runner_time
                except ntx.NetworkXNoPath:
                    continue
        return graph


# path any two points
class PathSegment(pyd.BaseModel):
    """Defines a path segment between two doors, with a travel duration."""

    path: tuple[str, str] = pyd.Field(
        title="Path nodes",
        description="""The endpoints of the path.""",
        examples=[("d1", "d2")],
    )
    duration_seconds: float = pyd.Field(
        title="Duration (seconds)",
        description="""The time in seconds to traverse the path segment.""",
        examples=[5.0],
        ge=0,
    )
    required_assets: Sequence[str] = pyd.Field(
        title="Required assets",
        description="""The required transport assets to traverse the path segment.""",
        examples=[["asset:lift", "inv:sample_tray", "hr:lab_assitant"]],
    )


def logical_graph(
    model: BimModel,
    door_list: Sequence[str],
    extra_paths: Sequence[PathSegment],
    runner_speed: float = DEFAULT_RUNNER_SPEED,
) -> ntx.Graph:
    """Construct a logical graph representation of the histopathology lab,
        with nodes representing doors and edge weights representing travel
        times in seconds.

    Args:
        model (BimModel): BimModel representation of the lab.
        door_list (Sequence[str]): List of doors to include in the logical graph, by name.
        runner_speed (float): Runner speed in m/s.
        extra_paths (Sequence[Path]): Paths connecting different floors of the lab.

    Returns:
        ntx.Graph: The logical graph for the lab.
    """
    target_levels = list(
        model.doors.loc[model.doors.door_name.isin(door_list)].floor.unique()
    )

    logical_graphs = {}
    # Build the logical graph for each target level and compose them
    for level in target_levels:
        s_model = ShapelyModel(model, level=level, include_doors=door_list)
        l_graph = s_model.logical_graph(runner_speed)
        logical_graphs[level] = l_graph

    full_logical_graph = ntx.compose_all(logical_graphs.values())

    # Add extra paths between levels
    for path in extra_paths:
        full_logical_graph.add_edge(
            *path.path,
            weight=path.duration_seconds,
            required_assets=path.required_assets
        )

    return full_logical_graph
