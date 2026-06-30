from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProjectRole = Literal["owner", "admin", "editor", "viewer"]


class MeResponse(BaseModel):
    subject: str
    role: Literal["admin", "user"]
    user_id: str | None
    email: str | None


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    status: str
    role: str | None
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    count: int


class ProjectMemberCreateRequest(BaseModel):
    user_id: str
    role: ProjectRole


class ProjectMemberResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: ProjectRole
    created_at: datetime


class ProjectMemberListResponse(BaseModel):
    members: list[ProjectMemberResponse]
    count: int
