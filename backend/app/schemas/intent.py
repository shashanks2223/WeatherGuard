from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryEnum(str, Enum):
    OUTDOOR_EXERCISE = "outdoor_exercise"
    TRAVEL = "travel"
    VULNERABLE_GROUPS = "vulnerable_groups"
    RECREATION = "recreation"
    GENERAL = "general"


class UserGroupEnum(str, Enum):
    ADULT = "adult"
    CHILD = "child"
    ELDERLY = "elderly"
    GENERAL = "general"


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    activity: str = Field(..., min_length=1, max_length=100)
    category: CategoryEnum = CategoryEnum.GENERAL
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    time_scope: str = Field("current", min_length=1, max_length=50)
    user_group: UserGroupEnum = UserGroupEnum.ADULT
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    raw_query: Optional[str] = Field(None, min_length=1, max_length=2000)


# Compatibility name used by the pre-existing graph and service modules.
UserIntent = Intent
