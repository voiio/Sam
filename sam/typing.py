from __future__ import annotations

import enum


class Roles(enum.StrEnum):
    """Roles in an LLM thread."""

    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class RunStatus(enum.StrEnum):
    """Assistant run status values."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REQUIRES_ACTION = "requires_action"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"
    INCOMPLETE = "incomplete"
