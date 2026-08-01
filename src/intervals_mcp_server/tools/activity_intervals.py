"""
Activity interval editing MCP tools for Intervals.icu.

These tools mutate the icu_intervals on an existing activity: bulk update,
single interval upsert, delete, and split.
"""

from typing import Any

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update Activity Intervals", readOnlyHint=False, destructiveHint=True
    )
)
async def update_activity_intervals(
    activity_id: str,
    intervals: list[dict[str, Any]],
    api_key: str = "",
    replace_all: bool = False,
) -> str:
    """Update intervals on an activity in bulk.

    Args:
        activity_id: The Intervals.icu activity ID.
        intervals: List of interval objects. See the Interval schema; common fields include
                   start_index, type ("WORK"/"REST"), label, moving_time, distance.
        api_key: Optional API key.
        replace_all: If True, replaces existing intervals; otherwise merges.
    """
    if not isinstance(intervals, list) or not intervals:
        return "Error: 'intervals' must be a non-empty list."

    params = {"all": True} if replace_all else None
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/intervals",
        api_key=api_key,
        method="PUT",
        params=params,
        data=intervals,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error updating intervals: {result.get('message', 'Unknown error')}"

    return f"Successfully updated {len(intervals)} interval(s) on activity {activity_id}."


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update Activity Interval", readOnlyHint=False, destructiveHint=False
    )
)
async def update_activity_interval(
    activity_id: str,
    interval_id: int,
    interval: dict[str, Any],
    api_key: str = "",
) -> str:
    """Update or create a single interval on an activity.

    Args:
        activity_id: The Intervals.icu activity ID.
        interval_id: Numeric interval ID. Use a new ID to create.
        interval: Interval payload (Interval schema).
        api_key: Optional API key.
    """
    if not isinstance(interval, dict) or not interval:
        return "Error: 'interval' must be a non-empty dictionary."

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/intervals/{interval_id}",
        api_key=api_key,
        method="PUT",
        data=interval,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error updating interval: {result.get('message', 'Unknown error')}"

    return f"Successfully upserted interval {interval_id} on activity {activity_id}."


@mcp.tool(
    annotations=ToolAnnotations(
        title="Delete Activity Intervals", readOnlyHint=False, destructiveHint=True
    )
)
async def delete_activity_intervals(
    activity_id: str,
    interval_ids: list[int],
    api_key: str = "",
) -> str:
    """Delete one or more intervals from an activity.

    Args:
        activity_id: The Intervals.icu activity ID.
        interval_ids: List of interval IDs to remove.
        api_key: Optional API key.
    """
    if not isinstance(interval_ids, list) or not interval_ids:
        return "Error: 'interval_ids' must be a non-empty list."

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/delete-intervals",
        api_key=api_key,
        method="PUT",
        data=interval_ids,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error deleting intervals: {result.get('message', 'Unknown error')}"

    return f"Successfully deleted {len(interval_ids)} interval(s) from activity {activity_id}."


@mcp.tool(
    annotations=ToolAnnotations(
        title="Split Activity Interval", readOnlyHint=False, destructiveHint=False
    )
)
async def split_activity_interval(
    activity_id: str,
    split_at: int,
    api_key: str = "",
) -> str:
    """Split an interval into two at the given stream index.

    Args:
        activity_id: The Intervals.icu activity ID.
        split_at: Stream index at which to split the interval.
        api_key: Optional API key.
    """
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/split-interval",
        api_key=api_key,
        method="PUT",
        params={"splitAt": split_at},
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error splitting interval: {result.get('message', 'Unknown error')}"

    return f"Successfully split interval at index {split_at} on activity {activity_id}."
