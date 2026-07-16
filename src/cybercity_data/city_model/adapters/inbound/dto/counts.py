"""Summary counts DTO."""

from pydantic import BaseModel, ConfigDict


class Counts(BaseModel):
    """Summary counts for a city network."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organizations: int
    networks: int
    services: int
    links: int
