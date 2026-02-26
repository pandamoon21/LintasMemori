from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

JobProvider = Literal["gptk", "gpmc", "gp_disguise"]
JobStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "requires_credentials",
]


class AccountCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    email_hint: Optional[str] = Field(default=None, max_length=255)


class AccountOut(BaseModel):
    id: str
    label: str
    email_hint: Optional[str]
    is_active: bool
    has_gpmc_auth_data: bool
    has_gptk_cookie_jar: bool
    created_at: datetime
    updated_at: datetime


class SetGpmcAuthRequest(BaseModel):
    auth_data: str = Field(min_length=1)


class JobCreate(BaseModel):
    account_id: str
    provider: JobProvider
    operation: str = Field(min_length=1, max_length=120)
    params: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class JobOut(BaseModel):
    id: str
    account_id: str
    provider: JobProvider
    operation: str
    dry_run: bool
    params: Dict[str, Any]
    status: Union[JobStatus, str]
    progress: float
    message: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class CancelJobResponse(BaseModel):
    id: str
    status: str
    cancel_requested: bool


class CookieImportResponse(BaseModel):
    account_id: str
    cookies_imported: int


class HealthResponse(BaseModel):
    status: str
