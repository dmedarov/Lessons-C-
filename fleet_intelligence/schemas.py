from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel

InsightSeverity = Literal["info", "warning", "critical"]


class SuggestedAssignment(BaseModel):
    car_id: int
    plate_number: str
    model: str
    score: float
    reason_code: str
    reason_text: str
    scoring: Dict[str, float]
    start_time: str
    end_time: str


class FleetInsight(BaseModel):
    kind: str
    severity: InsightSeverity
    title: str
    body: str
    metric: Optional[Union[float, int]] = None


class FleetPulseExtended(BaseModel):
    active_trips: int
    pending_requests: int
    active_cars: int
    available_now: int
    busiest_car: Optional[str] = None
    insights: List[FleetInsight]
