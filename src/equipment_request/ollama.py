"""Ollama chat backend for model completions.

Posts to /api/chat with streaming disabled. The assistant text is
message.content. From this devcontainer the daemon is on the host, so the
default base URL is http://host.docker.internal:11434. Set OLLAMA_HOST to
override it; include the scheme.
"""

import json
import os
from typing import Literal
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

from equipment_request.adapters.model import ModelRequest, ModelResponse

_DEFAULT_HOST = "http://host.docker.internal:11434"
_MODEL = "mistral:7b"


class OllamaMessage(BaseModel):
    """One chat message returned by Ollama."""

    model_config = ConfigDict(extra="ignore")

    role: Literal["assistant"]
    content: str


class OllamaChatResponse(BaseModel):
    """Non-streaming /api/chat body. Extra timing fields are ignored."""

    model_config = ConfigDict(extra="ignore")

    message: OllamaMessage


class OllamaModel:
    """ModelAdapter that calls mistral:7b through the Ollama chat API."""

    def __init__(self, base_url: str | None = None) -> None:
        """Use base_url, else OLLAMA_HOST, else the host daemon."""
        if base_url is not None:
            host = base_url
        else:
            host = os.environ.get("OLLAMA_HOST", _DEFAULT_HOST)
        self._chat_url = host.rstrip("/") + "/api/chat"

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Send the prompt as one user message and return the assistant text."""
        body = {
            "model": _MODEL,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
        }
        http_request = Request(
            self._chat_url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(http_request) as response:
            payload = json.loads(response.read().decode())
        chat = OllamaChatResponse.model_validate(payload)
        return ModelResponse(text=chat.message.content)
