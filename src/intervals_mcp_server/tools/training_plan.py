"""
Training plan MCP tools for Intervals.icu.

Tools for getting/changing the athlete's active training plan, applying plan
changes to the calendar, and bulk-changing plans across multiple athletes
(coach use case).
"""

import json
from typing import Any

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.validation import resolve_athlete_id
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool(annotations=ToolAnnotations(title="Get Training Plan", readOnlyHint=True, destructiveHint=False))
async def get_training_plan(
    athlete_id: str = "",
    api_key: str = "",
) -> str:
    """Get the athlete's current training plan, if any."""
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/training-plan",
        api_key=api_key,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching training plan: {result.get('message', 'Unknown error')}"

    if not result:
        return f"No active training plan for athlete {athlete_id_to_use}."

    return json.dumps(result, indent=2, default=str)


@mcp.tool(annotations=ToolAnnotations(title="Change Training Plan", readOnlyHint=False, destructiveHint=False))
async def change_training_plan(
    athlete_id: str = "",
    api_key: str = "",
    training_plan_id: int = 0,
    training_plan_start_date: str = "",
    training_plan_alias: str = "",
) -> str:
    """Set or change the athlete's active training plan.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, defaults to env).
        api_key: Optional API key.
        training_plan_id: Numeric ID of the plan to activate (0 = leave unchanged / clear).
        training_plan_start_date: Plan start date in YYYY-MM-DD format.
        training_plan_alias: Optional alias/label for the plan instance.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    payload: dict[str, Any] = {"id": athlete_id_to_use}
    if training_plan_id:
        payload["training_plan_id"] = training_plan_id
    if training_plan_start_date:
        payload["training_plan_start_date"] = training_plan_start_date
    if training_plan_alias:
        payload["training_plan_alias"] = training_plan_alias

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/training-plan",
        api_key=api_key,
        method="PUT",
        data=payload,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error changing training plan: {result.get('message', 'Unknown error')}"

    return f"Successfully updated training plan for athlete {athlete_id_to_use}."


@mcp.tool(annotations=ToolAnnotations(title="Apply Plan Changes", readOnlyHint=False, destructiveHint=False))
async def apply_plan_changes(
    athlete_id: str = "",
    api_key: str = "",
) -> str:
    """Apply pending changes from the athlete's current plan to their calendar."""
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/apply-plan-changes",
        api_key=api_key,
        method="PUT",
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error applying plan changes: {result.get('message', 'Unknown error')}"

    return f"Successfully applied plan changes to calendar for athlete {athlete_id_to_use}."


@mcp.tool(annotations=ToolAnnotations(title="Apply Plan to Calendar", readOnlyHint=False, destructiveHint=False))
async def apply_plan_to_calendar(
    folder_id: int,
    start_date_local: str,
    athlete_id: str = "",
    api_key: str = "",
    extra_workouts: list[dict[str, Any]] | None = None,
) -> str:
    """Apply a plan (workout folder) to the athlete's calendar starting on a date.

    Args:
        folder_id: ID of the folder/plan to apply.
        start_date_local: Plan start date as ISO datetime, e.g. "2026-06-01T00:00:00".
        athlete_id: The Intervals.icu athlete ID (optional, defaults to env).
        api_key: Optional API key.
        extra_workouts: Optional list of extra one-off Workout objects to include alongside
                        the folder's workouts.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    payload: dict[str, Any] = {
        "folder_id": folder_id,
        "start_date_local": start_date_local,
    }
    if extra_workouts:
        payload["extra_workouts"] = extra_workouts

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/events/apply-plan",
        api_key=api_key,
        method="POST",
        data=payload,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error applying plan: {result.get('message', 'Unknown error')}"

    return f"Successfully applied plan (folder {folder_id}) starting {start_date_local} for athlete {athlete_id_to_use}."


@mcp.tool(annotations=ToolAnnotations(title="Change Athlete Plans (Bulk)", readOnlyHint=False, destructiveHint=False))
async def change_athlete_plans_bulk(
    plan_changes: list[dict[str, Any]],
    api_key: str = "",
) -> str:
    """Change training plans for multiple athletes at once (coach tool).

    Args:
        plan_changes: List of AthleteTrainingPlanUpdate objects. Each item should include
                      ``id`` (athlete ID) and any of ``training_plan_id``,
                      ``training_plan_start_date``, ``training_plan_alias``.
        api_key: Optional API key.
    """
    if not isinstance(plan_changes, list) or not plan_changes:
        return "Error: 'plan_changes' must be a non-empty list."

    result = await make_intervals_request(
        url="/athlete-plans",
        api_key=api_key,
        method="PUT",
        data=plan_changes,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error bulk-updating athlete plans: {result.get('message', 'Unknown error')}"

    return f"Successfully updated plans for {len(plan_changes)} athlete(s)."
