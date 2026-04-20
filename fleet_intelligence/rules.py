from __future__ import annotations

from collections import Counter
from typing import Any

from .schemas import FleetInsight


def _count_phrase(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def score_car(
    car: Any,
    *,
    utilization_minutes: dict[int, int],
    user_preferences: Counter[int],
) -> tuple[float, str, str, dict[str, float]]:
    car_id = int(car["id"])
    utilization = utilization_minutes.get(car_id, 0)
    max_utilization = max(utilization_minutes.values(), default=0)
    preference_hits = user_preferences.get(car_id, 0)

    low_utilization_bonus = 0.0
    if max_utilization > 0:
        low_utilization_bonus = round(((max_utilization - utilization) / max_utilization) * 20, 2)

    preference_bonus = min(preference_hits * 4, 12)
    overuse_penalty = 15 if utilization >= max(480, max_utilization * 0.75) and max_utilization > 0 else 0
    score = round(100 + low_utilization_bonus + preference_bonus - overuse_penalty, 2)

    if preference_hits and score >= 100:
        return (
            score,
            "usual_car_balanced",
            "Избрана е обичайната ти кола, без да претоварва флота.",
            {
                "base": 100,
                "low_utilization_bonus": low_utilization_bonus,
                "preference_bonus": float(preference_bonus),
                "overuse_penalty": float(overuse_penalty),
            },
        )
    if low_utilization_bonus > 0:
        return (
            score,
            "low_recent_utilization",
            "Избрана е свободна кола с по-ниско скорошно натоварване.",
            {
                "base": 100,
                "low_utilization_bonus": low_utilization_bonus,
                "preference_bonus": float(preference_bonus),
                "overuse_penalty": float(overuse_penalty),
            },
        )
    return (
        score,
        "available_balanced",
        "Избрана е свободна активна кола за този слот.",
        {
            "base": 100,
            "low_utilization_bonus": low_utilization_bonus,
            "preference_bonus": float(preference_bonus),
            "overuse_penalty": float(overuse_penalty),
        },
    )


def build_fleet_insights(
    *,
    active_trips: int,
    pending_requests: int,
    active_cars: int,
    available_now: int,
    utilization_minutes: dict[int, int],
    busiest_car: str | None,
) -> list[FleetInsight]:
    insights: list[FleetInsight] = []

    if pending_requests:
        insights.append(
            FleetInsight(
                kind="pending_bottleneck",
                severity="warning" if pending_requests >= 3 else "info",
                title=f"{pending_requests} {_count_phrase(pending_requests, 'заявка чака', 'заявки чакат')} решение",
                body="Първият ход за админ е да изчисти pending queue-а.",
                metric=pending_requests,
            )
        )

    if active_cars and available_now <= max(1, active_cars // 4):
        insights.append(
            FleetInsight(
                kind="low_availability",
                severity="warning",
                title="Свободните коли са малко",
                body="FleetFlow ще предпочита по-слабо натоварени коли за новите заявки.",
                metric=available_now,
            )
        )

    if utilization_minutes and busiest_car:
        max_minutes = max(utilization_minutes.values())
        min_minutes = min(utilization_minutes.values())
        if max_minutes >= 480 and max_minutes >= max(min_minutes * 2, 1):
            insights.append(
                FleetInsight(
                    kind="uneven_utilization",
                    severity="info",
                    title="Натоварването не е равномерно",
                    body=f"Най-използвана в последните 7 дни: {busiest_car}.",
                    metric=max_minutes,
                )
            )

    if active_trips:
        insights.append(
            FleetInsight(
                kind="active_mobility",
                severity="info",
                title=f"{active_trips} {_count_phrase(active_trips, 'активен курс', 'активни курса')}",
                body="Следи текущите курсове преди нови одобрения в същия времеви прозорец.",
                metric=active_trips,
            )
        )

    if not insights:
        insights.append(
            FleetInsight(
                kind="calm_fleet",
                severity="info",
                title="Флотът е спокоен",
                body="Няма видим bottleneck; следващият ход е стандартно одобрение на новите заявки.",
            )
        )

    return insights[:4]
