from __future__ import annotations

from fastapi import APIRouter, Depends

from production_readiness import evaluate_runtime_readiness
from schemas import ProductionReadinessResponse
from security import AuthContext, require_admin

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/readiness", response_model=ProductionReadinessResponse)
def production_readiness(_: AuthContext = Depends(require_admin)) -> ProductionReadinessResponse:
    return ProductionReadinessResponse(**evaluate_runtime_readiness())
