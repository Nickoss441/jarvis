"""The agent loop.

Each call to `Brain.turn(user_input)`:
  1. Logs the user input.
  2. Asks Claude what to do, given the conversation, system prompt, and tool
     schemas.
  3. If Claude returns text, returns it.
  4. If Claude requested tools, runs each tool through the policy engine,
     dispatches it, logs the result, and feeds results back to Claude.
  5. Repeats up to MAX_ITERATIONS.
"""
from datetime import date
from typing import Any, cast
from uuid import uuid4

from .config import Config
from .audit import AuditLog
from .memory import Conversation
from .policy import Policy
from .runtime import RuntimeOrchestrator, RuntimeToolError
from .runtime.retry import RetryPolicy
from .runtime.turn import RuntimeTurnContext
from .tools import ToolRegistry

MAX_ITERATIONS = 10
MAX_TOKENS = 2048

SYSTEM_PROMPT = """<identity>
You are Jarvis, a personal agent for {user_name}.
Today is {date}.
</identity>

<situational_awareness>
- Operator: {user_name}
- Local date: {date}
- Tool surface: {open_count} open tools, {gated_count} gated tools (regenerated each turn from the live registry).
- Every tool call passes a deterministic policy preflight before dispatch and is recorded to the append-only audit log.
</situational_awareness>

<tool_families>
{tool_inventory}
</tool_families>

<turn_structure>
1. Understand the request and current context.
2. Decide whether to answer directly, ask one clarifying question, or use a tool.
3. If a tool is needed, emit exactly one short text block that starts with "Thought:" and then call the tool.
4. Use tool results to continue until the task is resolved or a clarification is required.
</turn_structure>

<planning_rules>
- For scheduling, availability, reminder, or booking requests, check calendar_read before making a plan unless the user already supplied the needed timing context.
- Use calendar context to avoid conflicts before proposing bookings, reservations, or date-sensitive next steps.
- Prefer the smallest tool that resolves the request; do not chain gated tools speculatively.
- If a gated tool would be needed but is likely to be denied by current policy, name the gap to the user instead of attempting it.
</planning_rules>

<response_contract>
- Be concise.
- Ask one focused clarifying question rather than guessing.
- If a gated tool is denied by policy, explain that briefly and continue with safe alternatives.
- Do not claim a tool succeeded unless the tool result confirms it.
- All actions are logged to the audit log and can be replayed.
</response_contract>
"""


class Brain:
    def __init__(
        self,
        config: Config,
        audit: AuditLog,
        policy: Policy,
        tools: ToolRegistry,
        retry_policy: RetryPolicy | None = None,
        system_prompt_template: str | None = None,
    ):
        self.config = config
        self.audit = audit
        self.policy = policy
        self.tools = tools
        self.retry_policy = retry_policy or RetryPolicy()
        self.system_prompt_template = system_prompt_template or SYSTEM_PROMPT
        self.conversation = Conversation(storage_path=config.conversation_store_path)
        self.runtime = RuntimeOrchestrator(MAX_ITERATIONS)

        # Lazy import so test files that only touch audit/policy don't need
        # the anthropic package installed.
        import anthropic
        self.client = anthropic.Anthropic(
            api_key=(config.get_secret("ANTHROPIC_API_KEY") or config.anthropic_api_key)
        )

    def _tool_inventory(self) -> str:
        """Render the live tool registry as a tier-grouped bullet list.

        Generated each turn so the system prompt cannot drift from the
        actually-registered tools. Descriptions are truncated and any literal
        braces are escaped so the result is safe to feed through ``str.format``.
        """
        open_lines: list[str] = []
        gated_lines: list[str] = []
        for tool in sorted(self.tools.all(), key=lambda t: t.name):
            description = (tool.description or "").strip().splitlines()[0] if tool.description else ""
            if len(description) > 110:
                description = description[:107].rstrip() + "..."
            line = f"- {tool.name}: {description}" if description else f"- {tool.name}"
            if tool.tier == "gated":
                gated_lines.append(line)
            else:
                open_lines.append(line)
        sections: list[str] = []
        if open_lines:
            sections.append("open:\n" + "\n".join(open_lines))
        if gated_lines:
            sections.append("gated (require approval):\n" + "\n".join(gated_lines))
        rendered = "\n\n".join(sections) if sections else "(no tools registered)"
        return rendered.replace("{", "{{").replace("}", "}}")

    def _system(self) -> str:
        metadata = self.tools.metadata()
        return self.system_prompt_template.format(
            user_name=self.config.user_name,
            date=date.today().isoformat(),
            tool_inventory=self._tool_inventory(),
            open_count=metadata.get("open_count", 0),
            gated_count=metadata.get("gated_count", 0),
        )

    def _perceive(self, turn: RuntimeTurnContext) -> None:
        self.audit.append(
            "user_input",
            {"text": turn.user_input, "correlation_id": turn.correlation_id},
        )
        self.conversation.add_user(turn.user_input)

    def _plan(self, turn: RuntimeTurnContext) -> Any:
        turn.advance_iteration()
        turn.begin_react_cycle()
        # Anthropic types are stricter than our dynamic tool/message shapes.
        tools_payload: Any = self.tools.schemas()
        messages_payload: Any = self.conversation.messages
        return self.client.messages.create(
            model=self.config.model,
            max_tokens=MAX_TOKENS,
            system=self._system(),
            tools=tools_payload,
            messages=messages_payload,
        )

    @staticmethod
    def _content_blocks(response: Any) -> list[Any]:
        raw_content = getattr(response, "content", [])
        if isinstance(raw_content, list):
            return cast(list[Any], raw_content)
        if isinstance(raw_content, tuple):
            return list(cast(tuple[Any, ...], raw_content))
        return []

    @staticmethod
    def _normalize_thought_text(text: str) -> str:
        normalized = text.strip()
        if normalized.lower().startswith("thought:"):
            return normalized[len("thought:") :].strip()
        return normalized

    @classmethod
    def _ensure_thought_prefix(cls, text: str) -> str:
        normalized = cls._normalize_thought_text(text)
        if not normalized:
            return ""
        return f"Thought: {normalized}"

    def _observe(self, response: Any, correlation_id: str) -> list[dict[str, Any]]:
        blocks = self._content_blocks(response)
        text = self.runtime.text_from_blocks(blocks)
        stop_reason = str(getattr(response, "stop_reason", "unknown"))
        thought_text = self._normalize_thought_text(text)
        if stop_reason == "tool_use":
            if thought_text:
                # Record the model's reasoning text for the current ReAct cycle.
                self._active_turn.record_thought(thought_text)
        elif text.strip():
            self._active_turn.complete_react_cycle(final_text=text)
        content_blocks = [self._block_to_dict(b) for b in blocks]
        if stop_reason == "tool_use":
            for block in content_blocks:
                if block.get("type") == "text":
                    block["text"] = self._ensure_thought_prefix(str(block.get("text", "")))
        self.audit.append("llm_response", {
            "stop_reason": stop_reason,
            "content": content_blocks,
            "correlation_id": correlation_id,
        })
        self.conversation.add_assistant(content_blocks)
        return content_blocks

    def _preflight(self, name: str, args: dict[str, Any]):
        return self.policy.check_tool(name, args)

    def _dispatch(
        self,
        name: str,
        args: dict[str, Any],
        correlation_id: str | None = None,
        tool_use_id: str | None = None,
    ) -> Any:
        decision = self._preflight(name, args)
        self.audit.append("tool_call", {
            "name": name,
            "args": args,
            "correlation_id": correlation_id,
            "tool_use_id": tool_use_id,
            "policy": {"allowed": decision.allowed, "reason": decision.reason},
        })
        if not decision.allowed:
            return RuntimeToolError(
                kind="policy-denied",
                tool_name=name,
                message="policy preflight denied this tool call",
                detail=decision.reason,
            ).to_dict()

        tool = self.tools.get(name)
        if not tool:
            return RuntimeToolError(
                kind="tool-not-found",
                tool_name=name,
                message=f"no handler registered for '{name}'",
            ).to_dict()

        result: Any = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                result = tool.handler(**args)
                break
            except TypeError as e:
                result = RuntimeToolError(
                    kind="tool-bad-args",
                    tool_name=name,
                    message="tool called with wrong arguments",
                    detail=str(e),
                ).to_dict()
                break
            except Exception as e:
                if self.retry_policy.should_retry(attempt):
                    continue
                result = RuntimeToolError(
                    kind="tool-failure",
                    tool_name=name,
                    message=f"{e.__class__.__name__}: {e}",
                ).to_dict()

        self.audit.append(
            "tool_result",
            {
                "name": name,
                "result": result,
                "correlation_id": correlation_id,
                "tool_use_id": tool_use_id,
            },
        )
        return result

    def _dispatch_requested_tools(self, response: Any, turn: RuntimeTurnContext) -> list[dict[str, Any]]:
        tool_results: list[dict[str, Any]] = []
        blocks = self._content_blocks(response)
        for block in blocks:
            if getattr(block, "type", None) != "tool_use":
                continue
            raw_input = getattr(block, "input", {})
            tool_name = str(getattr(block, "name", ""))
            tool_use_id = getattr(block, "id", None)
            if not isinstance(raw_input, dict):
                result = RuntimeToolError(
                    kind="tool-bad-args",
                    tool_name=tool_name or "<unknown>",
                    message="tool input must be an object",
                    detail=f"got {type(raw_input).__name__}",
                ).to_dict()
                self.audit.append(
                    "tool_call",
                    {
                        "name": tool_name,
                        "args": raw_input,
                        "correlation_id": turn.correlation_id,
                        "tool_use_id": tool_use_id,
                        "policy": {"allowed": False, "reason": "invalid_tool_input"},
                    },
                )
                self.audit.append(
                    "tool_result",
                    {
                        "name": tool_name,
                        "result": result,
                        "correlation_id": turn.correlation_id,
                        "tool_use_id": tool_use_id,
                    },
                )
                tool_results.append(turn.add_tool_result(tool_use_id, result))
                continue

            args = cast(dict[str, Any], raw_input)
            turn.record_action(tool_name, args, tool_use_id=tool_use_id)
            result = self._dispatch(
                tool_name,
                args,
                correlation_id=turn.correlation_id,
                tool_use_id=tool_use_id,
            )
            turn.record_observation(tool_name, result, tool_use_id=tool_use_id)
            tool_results.append(turn.add_tool_result(tool_use_id, result))
        return tool_results

    def turn(self, user_input: str) -> str:
        """One conversational turn. Returns the agent's final text."""
        correlation_id = str(uuid4())
        turn = self.runtime.start_turn(user_input, correlation_id)
        self._active_turn = turn
        self._perceive(turn)

        while not turn.exhausted:
            response = self._plan(turn)

            self._observe(response, correlation_id)

            if getattr(response, "stop_reason", None) != "tool_use":
                blocks = self._content_blocks(response)
                return self.runtime.final_text_from_blocks(blocks)

            tool_results = self._dispatch_requested_tools(response, turn)
            turn.complete_react_cycle()
            self.conversation.add_tool_results(tool_results)

        return "(stopped after max iterations — task too long for one turn)"

    def run_tool(
        self,
        name: str,
        args: dict[str, Any],
        correlation_id: str | None = None,
        tool_use_id: str | None = None,
    ) -> Any:
        return self._dispatch(
            name,
            args,
            correlation_id=correlation_id,
            tool_use_id=tool_use_id,
        )

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        block_type = getattr(block, "type", "unknown")
        if block_type == "text":
            return {"type": "text", "text": getattr(block, "text", "")}
        if block_type == "tool_use":
            raw_input = getattr(block, "input", {})
            serialized_input: dict[str, Any]
            if isinstance(raw_input, dict):
                serialized_input = cast(dict[str, Any], raw_input)
            else:
                serialized_input = {"_raw": raw_input}
            return {
                "type": "tool_use",
                "id": getattr(block, "id", None),
                "name": str(getattr(block, "name", "")),
                "input": serialized_input,
            }
        return {"type": str(block_type)}
