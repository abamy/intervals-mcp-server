"""
Activity search and discovery tools for Intervals.icu.

These tools cover lookup operations beyond simple date-range listing:
text/tag search, interval search, neighbour activities, multi-fetch by ID,
and tag enumeration.
"""

import json
from typing import Any

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_activity_compact
from intervals_mcp_server.utils.validation import resolve_athlete_id

from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


def _format_activity_list(activities: list[dict[str, Any]], header: str) -> str:
    if not activities:
        return f"{header}\n(no results)"
    out = f"{header}\n\n"
    for activity in activities:
        if isinstance(activity, dict):
            out += format_activity_compact(activity) + "\n"
    return out


@mcp.tool(annotations=ToolAnnotations(title="Search Activities", readOnlyHint=True, destructiveHint=False))
async def search_activities(
    query: str,
    athlete_id: str = "",
    api_key: str = "",
    limit: int = 25,
    full: bool = False,
) -> str:
    """Search activities by name (case-insensitive) or by exact tag (prefix with ``#``).

    Args:
        query: Search query. Plain text searches activity names; prefix with ``#`` to match a tag exactly.
        athlete_id: The Intervals.icu athlete ID (optional, defaults to env)
        api_key: The Intervals.icu API key (optional, defaults to env)
        limit: Maximum number of results (default 25)
        full: If True, fetch full activity objects via /search-full; otherwise summary info.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    if not query:
        return "Error: query is required."

    endpoint = "search-full" if full else "search"
    params: dict[str, Any] = {"q": query, "limit": limit}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/{endpoint}",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error searching activities: {result.get('message', 'Unknown error')}"

    activities = result if isinstance(result, list) else []
    return _format_activity_list(activities, f"Activity search results for '{query}':")


@mcp.tool(annotations=ToolAnnotations(title="Interval Search", readOnlyHint=True, destructiveHint=False))
async def interval_search(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    min_secs: int,
    max_secs: int,
    min_intensity: int,
    max_intensity: int,
    athlete_id: str = "",
    api_key: str = "",
    interval_type: str = "",
    min_reps: int = 0,
    max_reps: int = 0,
    limit: int = 25,
) -> str:
    """Find activities containing intervals matching a duration and intensity window.

    Args:
        min_secs: Minimum interval duration in seconds.
        max_secs: Maximum interval duration in seconds.
        min_intensity: Minimum intensity percentage (e.g. 90 for 90% FTP).
        max_intensity: Maximum intensity percentage.
        athlete_id: The Intervals.icu athlete ID (optional, defaults to env)
        api_key: The Intervals.icu API key (optional, defaults to env)
        interval_type: Optional interval type filter (e.g. "WORK", "REST").
        min_reps: Minimum matching intervals required per activity (0 = no minimum).
        max_reps: Maximum matching intervals per activity (0 = no maximum).
        limit: Maximum number of activities to return.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    params: dict[str, Any] = {
        "minSecs": min_secs,
        "maxSecs": max_secs,
        "minIntensity": min_intensity,
        "maxIntensity": max_intensity,
        "limit": limit,
    }
    if interval_type:
        params["type"] = interval_type
    if min_reps:
        params["minReps"] = min_reps
    if max_reps:
        params["maxReps"] = max_reps

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/interval-search",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error in interval search: {result.get('message', 'Unknown error')}"

    activities = result if isinstance(result, list) else []
    header = (
        f"Activities with intervals matching {min_secs}-{max_secs}s @ "
        f"{min_intensity}-{max_intensity}%:"
    )
    return _format_activity_list(activities, header)


@mcp.tool(annotations=ToolAnnotations(title="Get Activities Around", readOnlyHint=True, destructiveHint=False))
async def get_activities_around(
    activity_id: str,
    athlete_id: str = "",
    api_key: str = "",
    route_id: int = 0,
    limit: int = 30,
) -> str:
    """List activities before and after a given activity, closest first.

    Args:
        activity_id: The reference activity ID (not returned in the result set).
        athlete_id: The Intervals.icu athlete ID (optional, defaults to env)
        api_key: The Intervals.icu API key (optional, defaults to env)
        route_id: Only return activities sharing this route (0 = no filter).
        limit: Maximum number of activities to return (default 30).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    if not activity_id:
        return "Error: activity_id is required."

    params: dict[str, Any] = {"activity_id": activity_id, "limit": limit}
    if route_id:
        params["route_id"] = route_id

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities-around",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching neighbour activities: {result.get('message', 'Unknown error')}"

    activities = result if isinstance(result, list) else []
    return _format_activity_list(activities, f"Activities around {activity_id}:")


@mcp.tool(annotations=ToolAnnotations(title="Get Activities by IDs", readOnlyHint=True, destructiveHint=False))
async def get_activities_by_ids(
    activity_ids: list[str],
    athlete_id: str = "",
    api_key: str = "",
    include_intervals: bool = False,
) -> str:
    """Fetch multiple activities by ID in a single call. Missing IDs are ignored.

    Args:
        activity_ids: List of Intervals.icu activity IDs.
        athlete_id: The Intervals.icu athlete ID (optional, defaults to env)
        api_key: The Intervals.icu API key (optional, defaults to env)
        include_intervals: If True, include icu_intervals/icu_groups in each activity.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    if not activity_ids:
        return "Error: activity_ids must be a non-empty list."

    ids_path = ",".join(activity_ids)
    params: dict[str, Any] = {}
    if include_intervals:
        params["intervals"] = True

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/{ids_path}",
        api_key=api_key,
        params=params or None,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching activities: {result.get('message', 'Unknown error')}"

    # Multi-fetch responses are richer than simple summaries; return JSON so callers
    # can inspect any field they need.
    return json.dumps(result, indent=2, default=str)


@mcp.tool(annotations=ToolAnnotations(title="Get Activity Tags", readOnlyHint=True, destructiveHint=False))
async def get_activity_tags(
    athlete_id: str = "",
    api_key: str = "",
) -> str:
    """List all tags that have been applied to the athlete's activities."""
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activity-tags",
        api_key=api_key,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching activity tags: {result.get('message', 'Unknown error')}"

    tags = result if isinstance(result, list) else []
    if not tags:
        return f"No activity tags found for athlete {athlete_id_to_use}."
    return "Activity tags:\n" + "\n".join(f"- {t}" for t in tags)
