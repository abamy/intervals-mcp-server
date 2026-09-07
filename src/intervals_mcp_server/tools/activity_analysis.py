"""
Activity analysis MCP tools for Intervals.icu.

These tools cover analytical endpoints for a single activity: curves
(HR/pace/power), segments, time-at-HR, weather, interval-stats, map,
power-vs-HR, training-load models, and best efforts.

Most tools return raw JSON because the response shapes vary widely and are
typically consumed by downstream callers for further analysis.
"""

import json
from typing import Any

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401


CURVE_TYPES = {"hr", "pace", "power", "power-multi"}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Curve", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_curve(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    activity_id: str,
    curve_type: str,
    api_key: str = "",
    gap: bool = False,
    fatigue: str = "",
    streams: str = "",
) -> str:
    """Get a single-activity best-effort curve (HR, pace, power, or multi-stream power).

    Args:
        activity_id: The Intervals.icu activity ID.
        curve_type: One of "hr", "pace", "power", "power-multi". "power-multi" returns
                    curves for multiple streams via the /power-curves endpoint.
        api_key: Optional API key.
        gap: For pace curves only. If True, returns gradient-adjusted pace curve.
        fatigue: For "power": one of "kj0", "kj1" to request a fatigued-curve variant.
                 For "power-multi": comma-separated list of "normal", "kj0", "kj1".
        streams: For "power-multi" only. Comma-separated list of stream names (default "watts").
    """
    if curve_type not in CURVE_TYPES:
        return (
            f"Invalid curve_type '{curve_type}'. Must be one of: {', '.join(sorted(CURVE_TYPES))}."
        )

    endpoint_map = {
        "hr": "hr-curve.json",
        "pace": "pace-curve.json",
        "power": "power-curve.json",
        "power-multi": "power-curves.json",
    }
    url = f"/activity/{activity_id}/{endpoint_map[curve_type]}"

    params: dict[str, Any] = {}
    if curve_type == "pace" and gap:
        params["gap"] = True
    if curve_type == "power" and fatigue:
        params["fatigue"] = fatigue
    if curve_type == "power-multi":
        if streams:
            params["types"] = streams
        if fatigue:
            params["fatigue"] = fatigue

    result = await make_intervals_request(url=url, api_key=api_key, params=params or None)

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching {curve_type} curve: {result.get('message', 'Unknown error')}"

    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Best Efforts", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_best_efforts(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    activity_id: str,
    stream: str,
    api_key: str = "",
    duration: int = 0,
    distance: float = 0.0,
    count: int = 0,
    min_value: float = 0.0,
    exclude_intervals: bool = False,
    start_index: int = 0,
    end_index: int = 0,
) -> str:
    """Find the best efforts (peak segments) within an activity's stream.

    Args:
        activity_id: The Intervals.icu activity ID.
        stream: Stream name to search (e.g. "watts", "heartrate", "velocity_smooth").
        api_key: Optional API key.
        duration: Duration of each effort in seconds (use 0 to omit).
        distance: Distance of each effort in meters (use 0 to omit).
        count: Maximum number of efforts to return (use 0 to omit).
        min_value: Minimum average value; intervals expand if specified (use 0 to omit).
        exclude_intervals: If True, ignore stream portions inside existing work intervals.
        start_index: First stream index to consider (0 = start).
        end_index: Last stream index to consider, exclusive (0 = end of stream).
    """
    if not stream:
        return "Error: stream is required."

    params: dict[str, Any] = {"stream": stream}
    if duration:
        params["duration"] = duration
    if distance:
        params["distance"] = distance
    if count:
        params["count"] = count
    if min_value:
        params["minValue"] = min_value
    if exclude_intervals:
        params["excludeIntervals"] = True
    if start_index:
        params["startIndex"] = start_index
    if end_index:
        params["endIndex"] = end_index

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/best-efforts",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching best efforts: {result.get('message', 'Unknown error')}"

    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Segments", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_segments(activity_id: str, api_key: str = "") -> str:
    """Get segments (e.g. Strava segments) detected within an activity."""
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/segments",
        api_key=api_key,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching segments: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Time at HR", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_time_at_hr(activity_id: str, api_key: str = "") -> str:
    """Get the per-bpm time-at-heart-rate distribution for an activity."""
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/time-at-hr",
        api_key=api_key,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching time-at-HR: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Weather Summary", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_weather_summary(
    activity_id: str,
    api_key: str = "",
    start_index: int = 0,
    end_index: int = 0,
) -> str:
    """Get weather conditions summary for an activity (or a slice of it).

    Args:
        activity_id: The Intervals.icu activity ID.
        api_key: Optional API key.
        start_index: First stream index to include (0 = start).
        end_index: Last stream index, exclusive (0 = end).
    """
    params: dict[str, Any] = {}
    if start_index:
        params["start_index"] = start_index
    if end_index:
        params["end_index"] = end_index

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/weather-summary",
        api_key=api_key,
        params=params or None,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching weather summary: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Interval Stats", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_interval_stats(
    activity_id: str,
    start_index: int,
    end_index: int,
    api_key: str = "",
) -> str:
    """Compute interval-style stats (avg power, HR, etc.) for a sub-section of an activity.

    Args:
        activity_id: The Intervals.icu activity ID.
        start_index: First stream index of the section.
        end_index: Last stream index of the section (exclusive).
        api_key: Optional API key.
    """
    params = {"start_index": start_index, "end_index": end_index}
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/interval-stats",
        api_key=api_key,
        params=params,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching interval stats: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Map", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_map(
    activity_id: str,
    api_key: str = "",
    bounds: str = "",
    bounds_only: bool = False,
    weather: bool = False,
) -> str:
    """Get activity map data (latlngs and/or bounds, optionally with weather points).

    Args:
        activity_id: The Intervals.icu activity ID.
        api_key: Optional API key.
        bounds: Comma-separated bounding box "left,top,right,bottom" to clip points to.
        bounds_only: If True, return only the map bounds, no latlngs.
        weather: If True, include weather points if available.
    """
    params: dict[str, Any] = {}
    if bounds:
        params["bounds"] = bounds
    if bounds_only:
        params["boundsOnly"] = True
    if weather:
        params["weather"] = True

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/map",
        api_key=api_key,
        params=params or None,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching activity map: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Power vs HR", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_power_vs_hr(activity_id: str, api_key: str = "") -> str:
    """Get the power-vs-heart-rate scatter data for an activity."""
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/power-vs-hr.json",
        api_key=api_key,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching power-vs-HR: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity HR Load Model", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_hr_load_model(activity_id: str, api_key: str = "") -> str:
    """Get the heart-rate-based training-load model for an activity."""
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/hr-load-model",
        api_key=api_key,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching HR load model: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Activity Power Spike Model", read_only_hint=True, destructive_hint=False
    )
)
async def get_activity_power_spike_model(activity_id: str, api_key: str = "") -> str:
    """Get the power-spike-detection model for an activity."""
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/power-spike-model",
        api_key=api_key,
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching power spike model: {result.get('message', 'Unknown error')}"
    return json.dumps(result, default=str)
