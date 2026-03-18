from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    OPERATOR = "operator"
    SALES = "sales"
    MANAGER = "manager"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    INVALID = "invalid"


class OpportunityStage(str, Enum):
    INITIAL = "initial"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class ContentTaskType(str, Enum):
    COPYWRITING = "copywriting"
    IMAGE = "image"
    VIDEO_SCRIPT = "video_script"


class ContentTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class KbMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
