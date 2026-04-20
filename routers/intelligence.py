from __future__ import annotations

from fastapi import APIRouter, Depends

from db import get_conn
from fleet_intelligence.schemas import FleetPulseExtended
from fleet_intelligence.service import fleet_pulse
from security import AuthContext, require_admin

router = APIRouter(prefix="/admin/intelligence", tags=["intelligence"])


@router.get("/pulse", response_model=FleetPulseExtended)
def admin_intelligence_pulse(_: AuthContext = Depends(require_admin)) -> FleetPulseExtended:
    with get_conn() as conn:
        return fleet_pulse(conn)
