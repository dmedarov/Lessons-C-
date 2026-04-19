from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["employee", "fleet_admin"]
ReservationStatus = Literal["pending", "approved", "checked_out", "returned", "rejected", "cancelled"]
BlackoutKind = Literal["service", "maintenance", "inspection", "blocked"]


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: str
    role: Role
    expires_in: int


class SetupStatusResponse(BaseModel):
    has_admin: bool


class BootstrapAdminPayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserCreatePayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "employee"
    email: Optional[str] = Field(default=None, max_length=254)


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: Role
    active: bool
    email: Optional[str] = None
    created_at: str


class PasswordChangePayload(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminPasswordResetPayload(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    reason: Optional[str] = Field(default=None, max_length=500)


class UserRoleChangePayload(BaseModel):
    role: Role
    reason: Optional[str] = Field(default=None, max_length=500)


class UserAuditResponse(BaseModel):
    id: int
    actor_id: int
    actor_display_name: str
    target_user_id: int
    action: str
    reason: Optional[str] = None
    at: str


class AdminHandoffPayload(BaseModel):
    demote_self: bool = True
    reason: Optional[str] = Field(default=None, max_length=500)


class AdminHandoffResponse(BaseModel):
    previous_admin: UserResponse
    next_admin: UserResponse
    demote_self: bool


class CarCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=2, max_length=100)


class CarNotesPayload(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)


class CarBlackoutCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    kind: BlackoutKind = "maintenance"
    reason: Optional[str] = Field(default=None, max_length=500)


class BlackoutUpdatePayload(BaseModel):
    start_time: datetime
    end_time: datetime
    kind: BlackoutKind = "maintenance"
    reason: Optional[str] = Field(default=None, max_length=500)


class CarBlackoutResponse(BaseModel):
    id: int
    car_id: int
    kind: BlackoutKind
    start_time: str
    end_time: str
    reason: Optional[str] = None
    active: bool
    created_by_id: int
    created_at: str


class ReservationCreate(BaseModel):
    car_id: int
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = Field(default=None, max_length=500)


class DecisionPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class BulkDecisionPayload(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    reason: Optional[str] = Field(default=None, max_length=500)


class BulkDecisionItem(BaseModel):
    id: int
    status: Literal["approved", "rejected", "skipped"]
    error: Optional[str] = None


class BulkDecisionResponse(BaseModel):
    results: list[BulkDecisionItem]
    succeeded: int
    failed: int


class LifecycleNotePayload(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


class NotificationResponse(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    reservation_id: Optional[int] = None
    read_at: Optional[str] = None
    created_at: str
