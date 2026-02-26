from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

JobProvider = Literal["gptk", "gpmc", "gp_disguise", "pipeline", "indexer", "advanced"]
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


class SetCookiesPasteRequest(BaseModel):
    cookie_string: str = Field(min_length=1)


class SessionRefreshRequest(BaseModel):
    source_path: str = Field(default="/", min_length=1)


class SessionRefreshResponse(BaseModel):
    account_id: str
    session_state: dict[str, Any]


class JobCreate(BaseModel):
    account_id: str
    provider: JobProvider
    operation: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class JobEventOut(BaseModel):
    id: str
    job_id: str
    level: str
    message: str
    progress: Optional[float]
    created_at: datetime


class JobOut(BaseModel):
    id: str
    account_id: str
    provider: str
    operation: str
    dry_run: bool
    params: dict[str, Any]
    status: str
    progress: float
    message: Optional[str]
    result: Optional[dict[str, Any]]
    error: Optional[dict[str, Any]]
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    events: list[JobEventOut] = Field(default_factory=list)


class CancelJobResponse(BaseModel):
    id: str
    status: str
    cancel_requested: bool


class CookieImportResponse(BaseModel):
    account_id: str
    cookies_imported: int


class ExplorerSourceOut(BaseModel):
    id: str
    label: str
    icon: str


class ExplorerAlbumOut(BaseModel):
    media_key: str
    title: Optional[str]
    owner_actor_id: Optional[str]
    item_count: Optional[int]
    creation_timestamp: Optional[int]
    modified_timestamp: Optional[int]
    is_shared: bool
    thumb: Optional[str]


class ExplorerItem(BaseModel):
    media_key: str
    dedup_key: Optional[str]
    timestamp_taken: Optional[int]
    timestamp_uploaded: Optional[int]
    file_name: Optional[str]
    size: Optional[int]
    type: Optional[str]
    is_archived: bool
    is_favorite: bool
    is_trashed: bool
    album_ids: list[str] = Field(default_factory=list)
    thumb_url: Optional[str]
    owner: Optional[str]
    space_flags: dict[str, Any] = Field(default_factory=dict)
    source: str


class ExplorerItemDetail(ExplorerItem):
    raw_item: dict[str, Any] = Field(default_factory=dict)


class ExplorerItemsResponse(BaseModel):
    items: list[ExplorerItem]
    next_cursor: Optional[str]
    total_returned: int


class ExplorerQuery(BaseModel):
    source: Optional[str] = None
    album_id: Optional[str] = None
    search: Optional[str] = None
    date_from: Optional[int] = None
    date_to: Optional[int] = None
    media_type: Optional[str] = None
    owned: Optional[bool] = None
    favorite: Optional[bool] = None
    archived: Optional[bool] = None
    trashed: Optional[bool] = None
    sort: str = "timestamp_desc"
    page_cursor: Optional[str] = None
    page_size: int = Field(default=120, ge=1, le=500)


class ExplorerIndexRefreshRequest(BaseModel):
    account_id: str
    max_items: int = Field(default=3000, ge=100, le=50000)
    include_album_members: bool = False
    force_full: bool = False


class ActionPreviewRequest(BaseModel):
    account_id: str
    query: Optional[ExplorerQuery] = None
    selected_media_keys: Optional[list[str]] = None
    action: str = Field(min_length=1, max_length=120)
    action_params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_targets(self) -> "ActionPreviewRequest":
        if not self.query and not self.selected_media_keys:
            raise ValueError("Either query or selected_media_keys is required")
        return self


class ActionPreviewResult(BaseModel):
    preview_id: str
    match_count: int
    sample_items: list[ExplorerItem]
    warnings: list[str] = Field(default_factory=list)
    requires_confirm: bool = True


class ActionCommitRequest(BaseModel):
    preview_id: str
    confirm: bool = False


class ActionCommitResponse(BaseModel):
    preview_id: str
    job_id: str
    status: str


class UploadPreviewRequest(BaseModel):
    account_id: str
    target: str | list[str]
    recursive: bool = False
    gpmc_upload_options: dict[str, Any] = Field(default_factory=dict)


class UploadPreviewResult(BaseModel):
    preview_id: str
    target_count: int
    sample_files: list[str]
    warnings: list[str] = Field(default_factory=list)
    requires_confirm: bool = True


class UploadCommitRequest(BaseModel):
    preview_id: str
    confirm: bool = False


class DisguiseUploadRequest(BaseModel):
    account_id: str
    input_files: list[str]
    disguise_type: Literal["image", "video"] = "image"
    separator: str = "FILE_DATA_BEGIN"
    output_policy: dict[str, Any] = Field(default_factory=dict)
    gpmc_upload_options: dict[str, Any] = Field(default_factory=dict)


class PipelinePreviewResult(BaseModel):
    preview_id: str
    input_count: int
    estimated_outputs: int
    sample_files: list[str]
    warnings: list[str] = Field(default_factory=list)
    requires_confirm: bool = True


class PipelineCommitRequest(BaseModel):
    preview_id: str
    confirm: bool = False


class AdvancedPreviewRequest(BaseModel):
    account_id: str
    provider: Literal["gptk", "gpmc", "gp_disguise"]
    operation: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] = Field(default_factory=dict)


class AdvancedPreviewResult(BaseModel):
    preview_id: str
    operation: str
    provider: str
    warnings: list[str] = Field(default_factory=list)
    requires_confirm: bool = True


class AdvancedCommitRequest(BaseModel):
    preview_id: str
    confirm: bool = False


class JobsStreamEvent(BaseModel):
    event_id: str
    type: Literal["job_event", "job_state"]
    job_id: str
    payload: dict[str, Any]
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
