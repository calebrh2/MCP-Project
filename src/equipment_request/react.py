"""ReAct loop for one equipment request.

Each model call returns a thought and an action. A tool action is checked,
called, and appended as an observation. finish stops the loop. After eight
calls without finish, the request is flagged for human review and is not
reflected on. A finished draft gets one more model call that checks it
against the tool observations.
"""

import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from equipment_request.adapters.model import ModelAdapter, ModelRequest

MAX_STEPS = 8
MAX_REQUEST_CHARS = 1_000
MAX_THOUGHT_CHARS = 2_000
_EMPLOYEE_ID = re.compile(r"^E-\d{4}$")
_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "react-v1.txt"
_REFLECT_PATH = Path(__file__).resolve().parent / "prompts" / "reflect-v2.txt"
_STEP_LIMIT_RESPONSE = (
    "Escalated for human review. The agent did not finish within 8 steps."
)
_REFLECTION_RESPONSE = (
    "Escalated for human review. The draft did not match the recorded tool results."
)

ToolCaller = Callable[[str, dict[str, Any]], Awaitable[object]]


class ListedTool(BaseModel):
    """One tool advertised by the MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any]


class EmployeeIdError(ValueError):
    """The employee id is not in the E-#### form."""


class GuardedRequest(BaseModel):
    """Request text after the size and character checks."""

    employee_id: str
    text: str


class ParsedStep(BaseModel):
    """One model reply: a thought and the action to take."""

    model_config = ConfigDict(extra="ignore")

    thought: str
    action: str
    action_input: dict[str, Any] = {}

    @field_validator("thought", "action")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """Reject an empty thought or action name."""
        if not value.strip():
            raise ValueError("thought and action are required")
        return value


class FinishInput(BaseModel):
    """The local finish action. Escalation carries a reason code."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "deny", "escalate"]
    response: str
    reason: str | None = None

    @model_validator(mode="after")
    def reason_matches_decision(self) -> Self:
        """Require a reason only when the decision is escalate."""
        if not self.response.strip():
            raise ValueError("response is required")
        if self.decision == "escalate":
            if self.reason is None or not self.reason.strip():
                raise ValueError("escalate requires reason")
        elif self.reason is not None:
            raise ValueError("reason is only allowed when escalating")
        return self


class TraceStep(BaseModel):
    """One Thought, Action, and Observation stored for the next prompt."""

    thought: str
    action: str
    action_input: dict[str, Any]
    observation: str


class Reflection(BaseModel):
    """Whether a finished draft matches the tool observations."""

    model_config = ConfigDict(extra="forbid")

    passes: bool
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        """A reflection has to say why it passed or failed."""
        if not value.strip():
            raise ValueError("reflection reason is required")
        return value


class ReactResult(BaseModel):
    """The decision, the trace file, and the steps that produced them."""

    decision: Literal["approve", "deny", "escalate"]
    response: str
    review_id: str | None
    trace_path: str
    steps: list[TraceStep]
    reflection: Reflection | None = None
    draft_decision: Literal["approve", "deny", "escalate"] | None = None
    draft_response: str | None = None


def guard_request(employee_id: str, text: str) -> GuardedRequest:
    """Reject a bad employee id and cap the request text at 1,000 characters.

    Control characters are removed. Newlines and tabs become spaces, then
    repeated spaces collapse. The cut happens after that cleanup.
    """
    if _EMPLOYEE_ID.fullmatch(employee_id) is None:
        raise EmployeeIdError("employee_id must match E-####")
    return GuardedRequest(employee_id=employee_id, text=_clean_text(text))


def parse_step(text: str) -> ParsedStep:
    """Read the first JSON object in a model reply."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model output is not a JSON object")
    try:
        payload: object = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("model output is not a JSON object") from exc
    return ParsedStep.model_validate(payload)


def build_prompt(
    request: GuardedRequest, steps: list[TraceStep], tools: list[ListedTool]
) -> str:
    """Fill the ReAct prompt with the listed tools, the request, and the trace."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return (
        template.replace("__EMPLOYEE_ID__", request.employee_id)
        .replace("__REQUEST_TEXT__", _fence(request.text))
        .replace("__TOOLS__", _render_tools(tools))
        .replace("__TRACE__", _render_trace(steps))
    )


async def run_react(
    model: ModelAdapter,
    call_tool: ToolCaller,
    tools: list[ListedTool],
    employee_id: str,
    request_text: str,
    traces_dir: Path,
    now: Callable[[], datetime] | None = None,
) -> ReactResult:
    """Run at most eight decision calls, reflect once if a draft finished, and write the trace."""
    guarded = guard_request(employee_id, request_text)
    catalog = {tool.name: tool for tool in tools}
    clock = now or (lambda: datetime.now(UTC))
    steps: list[TraceStep] = []
    flagged = False
    review_id: str | None = None

    async def ensure_flag(reason: str) -> str | None:
        """Call flag_for_human_review once per run and keep its review id."""
        nonlocal flagged, review_id
        if flagged:
            return review_id
        result = await call_tool(
            "flag_for_human_review",
            {
                "employee_id": guarded.employee_id,
                "request": guarded.text,
                "reason": reason,
            },
        )
        flagged = True
        review_id = _review_id(result)
        return review_id

    async def complete(
        decision: Literal["approve", "deny", "escalate"],
        response: str,
        recorded_review_id: str | None,
        *,
        reflect: bool,
    ) -> ReactResult:
        """Reflect on a finished draft, then write the trace.

        A step-limit stop passes reflect=False and does not call the model again.
        A failed reflection replaces the draft with an escalation.
        """
        reflection: Reflection | None = None
        draft_decision: Literal["approve", "deny", "escalate"] | None = None
        draft_response: str | None = None
        final_decision = decision
        final_response = response
        final_review = recorded_review_id
        if reflect:
            draft_decision = decision
            draft_response = response
            reflection = _reflect(model, guarded, steps, decision, response)
            if not reflection.passes:
                final_decision = "escalate"
                final_response = f"{_REFLECTION_RESPONSE} {reflection.reason}"
                final_review = await ensure_flag("reflection_failed")
        result = ReactResult(
            decision=final_decision,
            response=final_response,
            review_id=final_review,
            trace_path="",
            steps=steps,
            reflection=reflection,
            draft_decision=draft_decision,
            draft_response=draft_response,
        )
        path = _write_trace(traces_dir, guarded, result, clock())
        return result.model_copy(update={"trace_path": str(path)})

    for number in range(1, MAX_STEPS + 1):
        raw = model.complete(
            ModelRequest(prompt=build_prompt(guarded, steps, tools))
        ).text
        try:
            parsed = parse_step(raw)
        except ValueError as exc:
            steps.append(_failed_step(raw, str(exc)))
            if number == MAX_STEPS:
                return await complete(
                    "escalate",
                    _STEP_LIMIT_RESPONSE,
                    await ensure_flag("step_limit"),
                    reflect=False,
                )
            continue

        thought = parsed.thought[:MAX_THOUGHT_CHARS]
        parsed = _coerce_finish(parsed)
        if parsed.action == "finish":
            try:
                done = FinishInput.model_validate(parsed.action_input)
            except ValidationError as exc:
                steps.append(
                    TraceStep(
                        thought=thought,
                        action="finish",
                        action_input=parsed.action_input,
                        observation=str(exc),
                    )
                )
                if number == MAX_STEPS:
                    return await complete(
                        "escalate",
                        _STEP_LIMIT_RESPONSE,
                        await ensure_flag("step_limit"),
                        reflect=False,
                    )
                continue
            recorded = None
            if done.decision == "escalate":
                if done.reason is None:
                    raise ValueError("escalate requires reason")
                recorded = await ensure_flag(done.reason)
            steps.append(
                TraceStep(
                    thought=thought,
                    action="finish",
                    action_input=done.model_dump(exclude_none=True),
                    observation=done.response,
                )
            )
            return await complete(done.decision, done.response, recorded, reflect=True)

        if number == MAX_STEPS:
            steps.append(
                TraceStep(
                    thought=thought,
                    action=parsed.action,
                    action_input=parsed.action_input,
                    observation="step limit reached before an answer",
                )
            )
            return await complete(
                "escalate",
                _STEP_LIMIT_RESPONSE,
                await ensure_flag("step_limit"),
                reflect=False,
            )

        if parsed.action not in catalog:
            steps.append(
                TraceStep(
                    thought=thought,
                    action=parsed.action,
                    action_input=parsed.action_input,
                    observation=f"unknown action: {parsed.action}",
                )
            )
            continue

        try:
            arguments = _validate_arguments(catalog[parsed.action], parsed.action_input)
        except ValueError as exc:
            steps.append(
                TraceStep(
                    thought=thought,
                    action=parsed.action,
                    action_input=parsed.action_input,
                    observation=str(exc),
                )
            )
            continue

        result = await call_tool(parsed.action, arguments)
        if parsed.action == "flag_for_human_review":
            flagged = True
            review_id = _review_id(result)
        steps.append(
            TraceStep(
                thought=thought,
                action=parsed.action,
                action_input=arguments,
                observation=_observation_text(result),
            )
        )

    return await complete(
        "escalate",
        _STEP_LIMIT_RESPONSE,
        await ensure_flag("step_limit"),
        reflect=False,
    )


def _clean_text(text: str) -> str:
    """Drop control characters, collapse spaces, and cut at the request cap."""
    kept: list[str] = []
    for char in text:
        if char in "\n\r\t":
            kept.append(" ")
        elif ord(char) < 32 or ord(char) == 127:
            continue
        else:
            kept.append(char)
    collapsed = re.sub(r" +", " ", "".join(kept)).strip()
    for token in (
        "__EMPLOYEE_ID__",
        "__REQUEST_TEXT__",
        "__TOOLS__",
        "__TRACE__",
        "__DECISION__",
        "__RESPONSE__",
    ):
        collapsed = collapsed.replace(token, "")
    return collapsed[:MAX_REQUEST_CHARS]


def _fence(text: str) -> str:
    """Escape markup so inserted text cannot close a prompt tag."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _validate_arguments(tool: ListedTool, payload: dict[str, Any]) -> dict[str, Any]:
    """Check a payload against the input schema the server advertised."""
    raw_properties = tool.input_schema.get("properties", {})
    properties = raw_properties if isinstance(raw_properties, dict) else {}
    raw_required = tool.input_schema.get("required", [])
    required = raw_required if isinstance(raw_required, list) else []
    missing = [str(name) for name in required if name not in payload]
    if missing:
        raise ValueError(
            f"invalid arguments for {tool.name}: missing {', '.join(missing)}"
        )
    unexpected = [name for name in payload if name not in properties]
    if unexpected:
        raise ValueError(
            f"invalid arguments for {tool.name}: unexpected {', '.join(unexpected)}"
        )
    for name, spec in properties.items():
        if name not in payload or not isinstance(spec, dict):
            continue
        schema_type = spec.get("type")
        if isinstance(schema_type, str):
            _check_schema_type(tool.name, name, payload[name], schema_type)
    return {str(name): payload[name] for name in properties if name in payload}


def _coerce_finish(parsed: ParsedStep) -> ParsedStep:
    """Treat a decision name used as the action as finish when the payload fits.

    Small models often put approve, deny, or escalate in the action field and
    the finish payload in action_input. That is still a finished answer.
    """
    if parsed.action == "finish":
        return parsed
    if parsed.action not in {"approve", "deny", "escalate"}:
        return parsed
    payload = dict(parsed.action_input)
    payload.setdefault("decision", parsed.action)
    try:
        FinishInput.model_validate(payload)
    except ValidationError:
        return parsed
    return parsed.model_copy(update={"action": "finish", "action_input": payload})


def _reflect(
    model: ModelAdapter,
    request: GuardedRequest,
    steps: list[TraceStep],
    decision: str,
    response: str,
) -> Reflection:
    """Ask the model whether the draft matches the observations."""
    raw = model.complete(
        ModelRequest(prompt=_reflection_prompt(request, steps, decision, response))
    ).text
    try:
        return _parse_reflection(raw)
    except ValueError as exc:
        return Reflection(passes=False, reason=str(exc))


def _reflection_prompt(
    request: GuardedRequest,
    steps: list[TraceStep],
    decision: str,
    response: str,
) -> str:
    """Fill the reflection prompt with the trace and the unfinished draft."""
    template = _REFLECT_PATH.read_text(encoding="utf-8")
    return (
        template.replace("__EMPLOYEE_ID__", request.employee_id)
        .replace("__REQUEST_TEXT__", _fence(request.text))
        .replace("__TRACE__", _render_trace(steps))
        .replace("__DECISION__", _fence(decision))
        .replace("__RESPONSE__", _fence(response))
    )


def _parse_reflection(text: str) -> Reflection:
    """Read the reflection JSON object from a model reply."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("reflection output is not a JSON object")
    try:
        payload: object = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("reflection output is not a JSON object") from exc
    reflection = Reflection.model_validate(payload)
    return reflection.model_copy(
        update={"reason": reflection.reason[:MAX_THOUGHT_CHARS]}
    )


def _failed_step(raw: str, observation: str) -> TraceStep:
    """Record an unparseable model reply without calling a tool."""
    return TraceStep(
        thought=raw[:MAX_THOUGHT_CHARS],
        action="",
        action_input={},
        observation=observation,
    )


def _review_id(result: object) -> str | None:
    """Read review_id when the flag tool returned a mapping."""
    if isinstance(result, dict):
        review_id = result.get("review_id")
        if isinstance(review_id, str):
            return review_id
    return None


def _observation_text(result: object) -> str:
    """Store a tool result as compact JSON, or as the string it already is."""
    if isinstance(result, str):
        return result
    return json.dumps(result)


def _render_tools(tools: list[ListedTool]) -> str:
    """Render the server catalog for the prompt."""
    if not tools:
        return "The server listed no tools."
    blocks: list[str] = []
    for tool in tools:
        blocks.append(
            "\n".join(
                [
                    f'<tool name="{tool.name}">',
                    f"<description>{tool.description}</description>",
                    f"<input_schema>{json.dumps(tool.input_schema)}</input_schema>",
                    "</tool>",
                ]
            )
        )
    return "\n".join(blocks)


def _check_schema_type(
    tool_name: str, field: str, value: object, schema_type: str
) -> None:
    """Reject a value whose Python type does not match the schema type."""
    if schema_type == "string" and isinstance(value, str):
        return
    if (
        schema_type == "integer"
        and isinstance(value, int)
        and not isinstance(value, bool)
    ):
        return
    if (
        schema_type == "number"
        and isinstance(value, int | float)
        and not isinstance(value, bool)
    ):
        return
    if schema_type == "boolean" and isinstance(value, bool):
        return
    if schema_type == "array" and isinstance(value, list):
        return
    if schema_type == "object" and isinstance(value, dict):
        return
    raise ValueError(
        f"invalid arguments for {tool_name}: {field} must be {schema_type}"
    )


def _render_trace(steps: list[TraceStep]) -> str:
    """Render prior steps as XML for the next model call."""
    if not steps:
        return "No steps yet."
    blocks: list[str] = []
    for index, step in enumerate(steps, start=1):
        blocks.append(
            "\n".join(
                [
                    f'<step n="{index}">',
                    f"<thought>{_fence(step.thought)}</thought>",
                    f"<action>{_fence(step.action)}</action>",
                    f"<action_input>{_fence(json.dumps(step.action_input))}</action_input>",
                    f"<observation>{_fence(step.observation)}</observation>",
                    "</step>",
                ]
            )
        )
    return "\n".join(blocks)


def _write_trace(
    traces_dir: Path,
    request: GuardedRequest,
    result: ReactResult,
    moment: datetime,
) -> Path:
    """Write Thought, Action, and Observation lines plus the final decision."""
    traces_dir.mkdir(parents=True, exist_ok=True)
    stamp = moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = traces_dir / f"react_traces_{stamp}.txt"
    lines = [f"request: {request.employee_id}: {request.text}", ""]
    for index, step in enumerate(result.steps, start=1):
        lines.extend(
            [
                f"step {index}",
                f"Thought: {step.thought}",
                f"Action: {step.action} {json.dumps(step.action_input)}",
                f"Observation: {step.observation}",
                "",
            ]
        )
    if result.draft_decision is not None:
        lines.append(f"draft_decision: {result.draft_decision}")
        lines.append(f"draft_response: {result.draft_response}")
    if result.reflection is not None:
        label = "passes" if result.reflection.passes else "fails"
        lines.append(f"reflection: {label}")
        lines.append(f"reflection_reason: {result.reflection.reason}")
    lines.append(f"decision: {result.decision}")
    lines.append(f"response: {result.response}")
    if result.review_id is not None:
        lines.append(f"review_id: {result.review_id}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
