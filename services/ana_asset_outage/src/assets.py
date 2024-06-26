from datetime import datetime
from enum import StrEnum
from typing import Optional

import pandas as pd
import pydantic as pyd
import pytz


class OutageState(StrEnum):
    """State of an outage (ended, current, planned, or cancelled)."""

    ENDED = "ended"
    CURRENT = "current"
    PLANNED = "planned"
    CANCELLED = "cancelled"


class NewOutageInputs(pyd.BaseModel):
    """Inputs for submitting a new outage."""

    asset_name: str = pyd.Field(
        title="Asset name", description="""Name of the asset.""", examples=["Lift 1"]
    )

    scenario: str = pyd.Field(
        default="default",
        title="Scenario",
        description="""The scenario to associate the outage with, defaults to 'default'.""",
    )

    start: float = pyd.Field(
        default_factory=lambda: datetime.now().timestamp(),
        title="Start",
        description="""UNIX timestamp representing the outage start.""",
    )

    end: float = pyd.Field(
        title="End", description="""UNIX timestamp representing the outage end."""
    )

    state: OutageState = pyd.Field(
        title="Stage",
        description="""\
State of the outage. Determines whether `start` and `end` are actual or planned timestamps.""",
    )

    updated_by: str = pyd.Field(
        title="Updated by",
        description="""The person who last updated the outage status in the database.""",
    )


class AssetOutage(NewOutageInputs):
    """Dataclass describing a an asset (e.g. lift) outage."""

    updated: float = pyd.Field(
        default_factory=lambda: datetime.now().timestamp(),
        title="Last updated",
        description="""The timestamp when the outage was last planned/reported/updated.""",
    )


class UpdateOutageInputs(pyd.BaseModel):
    """Inputs for updating data regarding an outage. Users can update the start time, end time,
    and/or state."""

    id: str = pyd.Field(
        title="Outage ID",
        description="""ObjectID of the existing outage entry in MongoDB.""",
        examples=["542c2b97bac0595474108b48"],
    )

    start: Optional[float] = pyd.Field(
        default=None,
        title="Start",
        description="""UNIX timestamp representing the outage start.""",
    )

    end: Optional[float] = pyd.Field(
        default=None,
        title="End",
        description="""UNIX timestamp representing the outage end.""",
    )

    state: Optional[OutageState] = pyd.Field(
        default=None,
        title="Stage",
        description="""\
State of the outage. Determines whether `start` and `end` are actual or planned timestamps.""",
    )

    updated_by: str = pyd.Field(
        title="Updated by",
        description="""The person who last updated the outage status in the database.""",
    )


class NewOutageResult(pyd.BaseModel):
    """Result of a `submit()` function call. Web services should use HTTP 202 Accepted."""

    id: str = pyd.Field(
        title="Job ID",
        description="ObjectID of the BIM job in the MongoDB database.",
        examples=["542c2b97bac0595474108b48"],
    )


class SearchInputs(pyd.BaseModel):
    """Inputs for searching for a list of outages."""

    asset_name: Optional[str] = pyd.Field(
        default=None,
        title="Asset name",
        description="""Name of the asset.""",
        examples=["Lift 1"],
    )

    scenario: Optional[str] = pyd.Field(
        default=None,
        title="Scenario",
        description="""The scenario to associate the outage with, defaults to 'default'.""",
    )

    from_time: Optional[float] = pyd.Field(
        default=None,
        title="From",
        description="""Return outages with an end time later than this timestamp, if provided.""",
    )

    to_time: Optional[float] = pyd.Field(
        default=None,
        title="To",
        description="""\
Return outages with an start time earlier than this timestamp, if provided.""",
    )

    include_cancelled: bool = pyd.Field(
        default=False,
        title="Include cancelled",
        description="""Whether or not to include cancelled outages in the search results.""",
    )
