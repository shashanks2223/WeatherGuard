from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SeverityLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AppliesTo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    activities: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    user_groups: List[str] = Field(default_factory=list)


ConditionScalar = Union[float, int, str]
ConditionValue = Union[ConditionScalar, List[ConditionScalar]]


class PolicyCondition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field: str = Field(..., min_length=1, max_length=100)
    operator: str = Field(..., min_length=1, max_length=30)
    value: ConditionValue
    secondary_value: Optional[ConditionValue] = None
    description: Optional[str] = Field(None, min_length=1, max_length=500)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        allowed = {">=", "<=", ">", "<", "==", "!=", "between", "in"}
        if value not in allowed:
            raise ValueError(f"unsupported policy operator: {value}")
        return value

    @field_validator("secondary_value")
    @classmethod
    def require_numeric_range_bound(cls, value, info):
        if value is not None and info.data.get("operator") == "between":
            if not isinstance(value, (int, float)):
                raise ValueError("between secondary_value must be numeric")
        return value

    def get(self, key: str, default=None):
        value = getattr(self, key, None)
        return default if value is None else value


class CompositeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_violations_to_trigger: int = Field(..., ge=1)
    rules: List[PolicyCondition] = Field(..., min_length=1)

    def get(self, key: str, default=None):
        value = getattr(self, key, None)
        return default if value is None else value


class PolicyConditions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all: Optional[List[PolicyCondition]] = Field(None, min_length=1)
    any: Optional[List[PolicyCondition]] = Field(None, min_length=1)
    composite_profile: Optional[CompositeProfile] = None

    @model_validator(mode="after")
    def require_condition_block(self) -> "PolicyConditions":
        if self.all is None and self.any is None and self.composite_profile is None:
            raise ValueError("policy conditions require all, any, or composite_profile")
        return self

    # Keeps the pre-existing evaluator compatible while conditions remain typed.
    def __contains__(self, key: str) -> bool:
        return getattr(self, key, None) is not None

    def get(self, key: str, default=None):
        value = getattr(self, key, None)
        return default if value is None else value

    def __getitem__(self, key: str):
        value = getattr(self, key, None)
        if value is None:
            raise KeyError(key)
        return value


class PolicyGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=200)
    recommendation: str = Field(..., min_length=1, max_length=2000)
    advisory_notes: Optional[str] = Field(None, min_length=1, max_length=2000)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., min_length=1, max_length=100)
    version: str = Field("1.0", min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    applies_to: AppliesTo
    conditions: PolicyConditions
    severity: SeverityLevel
    priority: int = Field(50, ge=0)
    guidance: PolicyGuidance
    evidence_fields: List[str] = Field(default_factory=list)


class PolicyMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(..., min_length=1)
    policy_name: str = Field(..., min_length=1)
    severity: SeverityLevel
    priority: int = Field(..., ge=0)
    matched: bool
    evaluated_reasons: List[str] = Field(default_factory=list)
    policy_obj: Policy
