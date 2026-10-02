"""Unit tests for the Ollama chat adapter, with the HTTP call mocked."""

import json
import os
from unittest.mock import MagicMock, patch

from equipment_request.adapters.model import ModelRequest
from equipment_request.ollama import OllamaModel


def test_complete_posts_mistral_chat_and_returns_content() -> None:
    """complete sends mistral:7b with stream off and returns message.content."""
    payload = json.dumps(
        {
            "message": {
                "role": "assistant",
                "content": "Alex Chen is an individual contributor.",
            }
        }
    ).encode()
    response = MagicMock()
    response.read.return_value = payload
    response.__enter__.return_value = response
    response.__exit__.return_value = None
    environ = os.environ.copy()
    environ.pop("OLLAMA_HOST", None)

    with (
        patch.dict(os.environ, environ, clear=True),
        patch("equipment_request.ollama.urlopen", return_value=response) as urlopen,
    ):
        result = OllamaModel().complete(ModelRequest(prompt="Who is E-1001?"))

    sent = urlopen.call_args.args[0]
    assert sent.full_url == "http://host.docker.internal:11434/api/chat"
    body = json.loads(sent.data.decode())
    assert body == {
        "model": "mistral:7b",
        "messages": [{"role": "user", "content": "Who is E-1001?"}],
        "stream": False,
    }
    assert result.text == "Alex Chen is an individual contributor."
