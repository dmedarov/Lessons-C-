from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import metrics
from .rules import build_fleet_insights, score_car
from .schemas import FleetPulseExtended, SuggestedAssignment


def suggest_best_car(conn: Any, *, user_id: int, start: datetime, end: datetime) -> SuggestedAssignment | None:
    start_iso = metrics.to_utc_iso(start)
    end_iso = metrics.to_utc_iso(end)
    unavailable = metrics.unavailable_car_ids(conn, start_iso, end_iso)
    candidates = [car for car in metrics.active_cars(conn) if int(car["id"]) not in unavailable]
    if not candidates:
        return None

    utilization = metrics.recent_utilization_minutes(conn)
    preferences = metrics.user_car_preferences(conn, user_id)
    scored: list[SuggestedAssignment] = []
    for car in candidates:
        score, reason_code, reason_text, scoring = score_car(
            car,
            utilization_minutes=utilization,
            user_preferences=preferences,
        )
        scored.append(
            SuggestedAssignment(
                car_id=int(car["id"]),
                plate_number=str(car["plate_number"]),
                model=str(car["model"]),
                score=score,
                reason_code=reason_code,
                reason_text=reason_text,
                scoring=scoring,
                start_time=start_iso,
                end_time=end_iso,
            )
        )

    return sorted(scored, key=lambda item: (-item.score, item.car_id))[0]


def fleet_pulse(conn: Any) -> FleetPulseExtended:
    now = datetime.now(timezone.utc)
    active_cars = metrics.active_cars(conn)
    active_trips = metrics.active_trip_count(conn)
    pending_requests = metrics.pending_request_count(conn)
    available_now = max(len(active_cars) - active_trips, 0)
    utilization = metrics.recent_utilization_minutes(conn, now=now)
    busiest_car = metrics.busiest_car_label(conn)

    return FleetPulseExtended(
        active_trips=active_trips,
        pending_requests=pending_requests,
        active_cars=len(active_cars),
        available_now=available_now,
        busiest_car=busiest_car,
        insights=build_fleet_insights(
            active_trips=active_trips,
            pending_requests=pending_requests,
            active_cars=len(active_cars),
            available_now=available_now,
            utilization_minutes=utilization,
            busiest_car=busiest_car,
        ),
    )
