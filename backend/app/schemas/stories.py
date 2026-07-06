"""API contracts for Career Story Intelligence."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.knowledge import EntityType


class StoryStatus(StrEnum):
    """Human-reviewed lifecycle for a Career Story."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class StoryChapterInput(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    summary: str | None = Field(default=None, max_length=4000)
    position: int = Field(ge=0)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def dates_are_ordered(self) -> StoryChapterInput:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("chapter start_date must not be after end_date")
        return self


class StoryMembershipInput(BaseModel):
    entity_type: EntityType
    entity_id: uuid.UUID
    chapter_position: int | None = Field(default=None, ge=0)
    role: str | None = Field(default=None, max_length=256)
    rationale: str = Field(min_length=3, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class StoryCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    summary: str = Field(min_length=1, max_length=10_000)
    primary_goal: str | None = Field(default=None, max_length=4000)
    transformation: str | None = Field(default=None, max_length=4000)
    confidence: float = Field(default=1, ge=0, le=1)
    chapters: list[StoryChapterInput] = Field(default_factory=list)
    memberships: list[StoryMembershipInput] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class StoryUpdateRequest(BaseModel):
    summary: str | None = Field(default=None, min_length=1, max_length=10_000)
    primary_goal: str | None = Field(default=None, max_length=4000)
    transformation: str | None = Field(default=None, max_length=4000)


class StoryRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)


class StoryMergeRequest(BaseModel):
    story_ids: list[uuid.UUID] = Field(min_length=2)
    title: str | None = Field(default=None, min_length=1, max_length=256)
    summary: str | None = Field(default=None, min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def stories_are_unique(self) -> StoryMergeRequest:
        if len(set(self.story_ids)) != len(self.story_ids):
            raise ValueError("story_ids must be unique")
        return self


class StorySplitRequest(BaseModel):
    membership_ids: list[uuid.UUID] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=256)
    summary: str | None = Field(default=None, min_length=1, max_length=10_000)


class StoryChapterView(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None
    position: int
    start_date: date | None
    end_date: date | None


class StoryMembershipView(BaseModel):
    id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID
    chapter_id: uuid.UUID | None
    label: str
    organization: str | None = None
    role: str | None
    rationale: str
    confidence: float


class StoryEvidenceView(BaseModel):
    id: uuid.UUID
    evidence_item_id: uuid.UUID
    title: str
    evidence_type: str
    verification_status: str
    source_url: str | None
    excerpt: str | None
    relationship_type: str


class StoryView(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    primary_goal: str | None
    transformation: str | None
    confidence: float
    status: StoryStatus
    chapters: list[StoryChapterView] = Field(default_factory=list)
    memberships: list[StoryMembershipView] = Field(default_factory=list)
    evidence: list[StoryEvidenceView] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class StoryDiscoveryResponse(BaseModel):
    stories: list[StoryView]
    experiences_considered: int
    signals_used: list[str]
    explanation: str
