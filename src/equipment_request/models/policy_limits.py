"""Policy limits returned for one role."""

from typing import Self

from pydantic import BaseModel, field_validator, model_validator

CATALOG_ITEMS = ("laptop", "monitor", "docking_station", "headset")


class PolicyLimit(BaseModel):
    """Cap and refresh interval for one catalog item."""

    item: str
    max_on_file: int
    refresh_years: int

    @field_validator("item")
    @classmethod
    def item_in_catalog(cls, value: str) -> str:
        """Keep policy rows inside the equipment catalog."""
        if value not in CATALOG_ITEMS:
            raise ValueError("item must be a catalog item")
        return value

    @field_validator("max_on_file", "refresh_years")
    @classmethod
    def positive(cls, value: int) -> int:
        """A limit of zero is not a policy row."""
        if value < 1:
            raise ValueError("policy limits must be at least 1")
        return value


class PolicyLimits(BaseModel):
    """Limits for one role, or a not-found result when the role has no policy."""

    role: str
    found: bool
    limits: list[PolicyLimit] = []

    @model_validator(mode="after")
    def found_role_has_catalog_rows(self) -> Self:
        """A known role lists each catalog item once; an unknown role has no rows."""
        items = [row.item for row in self.limits]
        if self.found:
            if items != list(CATALOG_ITEMS):
                raise ValueError(
                    "a found role requires laptop, monitor, docking_station, headset"
                )
        elif self.limits:
            raise ValueError("an unknown role has no policy rows")
        return self
