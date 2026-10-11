"""Target interface for language-model backends.

Domain schemas live in equipment_request.models. This module is the adapter
the agent calls; each backend translates its own API into these types.
"""

from typing import Protocol

from pydantic import BaseModel


class ModelRequest(BaseModel):
    """Prompt sent to a model backend."""

    prompt: str


class ModelResponse(BaseModel):
    """Text returned by a model backend."""

    text: str


class ModelAdapter(Protocol):
    """What the agent calls. Each backend adapts its own API to this."""

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return the model's text for this prompt."""
        ...
