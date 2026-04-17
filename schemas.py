from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ReservationStatus = Literal["pending", "approved", "rejected", "cancelled"]


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: str
    role: str
    expires_in: int


class CarCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=2, max_length=100)


class ReservationCreate(BaseModel):
    car_id: int
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = Field(default=None, max_length=500)


class DecisionPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)
