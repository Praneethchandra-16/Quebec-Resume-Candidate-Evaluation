"""One interface, three backends.

    client = get_client()
    job = client.structured(JobDescription, system=..., user=...)

Every call returns a validated Pydantic object or raises. No free-form text is
ever parsed by hand. The provider is swappable because the agents only depend on
`structured()`, not on OpenAI or Anthropic specifics.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def _strictify(schema: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI strict mode requires additionalProperties:false and every
    property listed in `required`. Pydantic does not emit either."""
    if schema.get("type") == "object" or "properties" in schema:
        schema["additionalProperties"] = False
        props = schema.get("properties", {})
        if props:
            schema["required"] = list(props.keys())
    for key in ("properties", "$defs", "definitions"):
        for sub in schema.get(key, {}).values():
            if isinstance(sub, dict):
                _strictify(sub)
    for key in ("items", "additionalItems"):
        if isinstance(schema.get(key), dict):
            _strictify(schema[key])
    for key in ("anyOf", "oneOf", "allOf"):
        for sub in schema.get(key, []):
            if isinstance(sub, dict):
                _strictify(sub)
    return schema


def json_schema_for(model: Type[BaseModel]) -> Dict[str, Any]:
    return _strictify(model.model_json_schema())


class BaseClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def structured(self, model: Type[T], system: str, user: str) -> T:
        last_error = None
        for attempt in range(self.settings.max_retries):
            try:
                raw = self._call(model, system, user)
                return model.model_validate(raw)
            except (ValidationError, json.JSONDecodeError) as exc:
                # Feed the error back so the model can repair its own output.
                last_error = exc
                user = (
                    f"{user}\n\nYour previous response failed validation:\n{exc}\n"
                    f"Return JSON that conforms exactly to the schema."
                )
            except Exception as exc:  # network, rate limit
                last_error = exc
                time.sleep(2 ** attempt)
        raise LLMError(f"{model.__name__} failed after retries: {last_error}")

    def _call(self, model: Type[T], system: str, user: str) -> Dict[str, Any]:
        raise NotImplementedError


class OpenAIClient(BaseClient):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.openai_api_key, timeout=settings.request_timeout
        )

    def _call(self, model: Type[T], system: str, user: str) -> Dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": model.__name__,
                    "schema": json_schema_for(model),
                    "strict": True,
                },
            },
        )
        return json.loads(resp.choices[0].message.content)


class AnthropicClient(BaseClient):
    """Anthropic has no json_schema response_format, so we force a single
    tool call whose input schema is the Pydantic schema. Same guarantee."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        import anthropic

        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=settings.request_timeout
        )

    def _call(self, model: Type[T], system: str, user: str) -> Dict[str, Any]:
        tool_name = f"emit_{model.__name__.lower()}"
        resp = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Emit a valid {model.__name__}.",
                    "input_schema": model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return block.input
        raise LLMError("Anthropic returned no tool_use block")


def get_client(settings: Settings = None) -> BaseClient:
    s = settings or get_settings()
    if s.provider == "openai":
        if not s.openai_api_key:
            raise LLMError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAIClient(s)
    if s.provider == "anthropic":
        if not s.anthropic_api_key:
            raise LLMError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
        return AnthropicClient(s)
    from app.llm.mock import MockClient

    return MockClient(s)
