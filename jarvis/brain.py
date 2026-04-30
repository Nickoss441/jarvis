ERROR_CODES = {
    # Protocol and conversation errors
    "ERR_TOOL_RESULT_PROTOCOL": {
        "code": 1001,
        "message": "A tool_result must immediately follow tool_use."
    },
    "ERR_TOOL_NOT_FOUND": {
        "code": 1002,
        "message": "Requested tool handler not found."
    },
    "ERR_TOOL_BAD_ARGS": {
        "code": 1003,
        "message": "Tool called with wrong arguments."
    },
    "ERR_TOOL_FAILURE": {
        "code": 1004,
        "message": "Tool handler raised an exception."
    },
    "ERR_POLICY_DENIED": {
        "code": 1005,
        "message": "Policy preflight denied this tool call."
    },
    "ERR_INVALID_TOOL_INPUT": {
        "code": 1006,
        "message": "Tool input must be an object."
    },
    "ERR_CONVERSATION_OVERFLOW": {
        "code": 1007,
        "message": "Conversation context window overflowed."
    },
    "ERR_LLM_API": {
        "code": 1008,
        "message": "LLM API error or timeout."
    },
    # Add more as needed
}

def make_error_payload(kind: str, detail: str = "") -> dict:
    info = ERROR_CODES.get(kind, {"code": 1999, "message": "Unknown error."})
    payload = {
        "type": "error",
        "error_code": info["code"],
        "error_type": kind,
        "message": info["message"],
    }
    if detail:
        payload["detail"] = detail
    return payload
class ToolResultProtocolError(Exception):
    """Raised when tool_result does not immediately follow tool_use as required by protocol."""
    def __init__(self, message: str = None):
        super().__init__(message or make_error_payload("ERR_TOOL_RESULT_PROTOCOL")["message"])

"""The agent loop.

Each call to `Brain.turn(user_input)`:
    1. Logs the user input.
    2. Asks Claude what to do, given the conversation, system prompt, and tool schemas.
    3. If Claude returns text, returns it.
    4. If Claude requested tools, runs each tool through the policy engine, dispatches it, logs the result, and feeds results back to Claude.
    5. Repeats up to MAX_ITERATIONS.

All errors are returned as structured payloads with a unique error code and type from ERROR_CODES.
Use make_error_payload(kind, detail) to generate a standard error response.
"""
# Export error codes for use by other modules
__all__ = ["Brain", "ERROR_CODES", "make_error_payload"]
from datetime import date
import re
from typing import Any, cast
from uuid import uuid4

from .config import Config
from .audit import AuditLog
from .memory import Conversation
from .ollama_adapter import OllamaModelRouter
from .policy import Policy
from .runtime import RuntimeOrchestrator, RuntimeToolError
from .runtime.retry import RetryPolicy
from .runtime.turn import RuntimeTurnContext
from .tools import ToolRegistry


class _OllamaTextBlock:
    """Minimal text block that mimics anthropic.types.TextBlock."""
    type = "text"
    def __init__(self, text: str):
        self.text = text


class _OllamaResponse:
    """Minimal response object that mimics anthropic.types.Message for text-only replies."""
    stop_reason = "end_turn"
    def __init__(self, text: str):
        self.content = [_OllamaTextBlock(text)]

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
- **Be direct and concise when needed.** Skip unnecessary preamble; get straight to the answer or action.
- Sound natural and conversational in normal chat, but prioritize clarity over verbosity.
- Be friendly and reassuring when the user sounds frustrated, tired, or casual.
- Ask one focused clarifying question rather than guessing.
- If a gated tool is denied by policy, explain that briefly and continue with safe alternatives.
- Do not claim a tool succeeded unless the tool result confirms it.
- Never simulate a transcript with multiple speakers (for example "User:" / "Jarvis:").
- Reply as Jarvis only; do not roleplay both sides of a conversation.
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

        self.ollama = OllamaModelRouter(
            base_url=config.ollama_base_url,
            timeout=config.ollama_timeout,
            fast_mode=config.ollama_fast_mode,
            num_ctx=config.ollama_num_ctx,
            num_predict=config.ollama_num_predict,
            keep_alive=config.ollama_keep_alive,
        ) if config.ollama_enabled else None
        if self.ollama:
            self.ollama.warm_load(config.ollama_warm_model)

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

        # Try Ollama first (free, local). In local-only mode, use Ollama on every
        # iteration and never fall back to Claude.
        if self.ollama and (turn.iteration == 1 or self.config.ollama_local_only):
            ollama_messages = self.conversation.trimmed_for_context(max_messages=12)
            text = self.ollama.chat(
                messages=ollama_messages,
                system=self._system(),
            )
            if text:
                return _OllamaResponse(text)

        if self.config.ollama_local_only:
            return _OllamaResponse(
                "Local-only mode is enabled and Ollama returned no response. "
                "Please check that Ollama is running and a model is loaded, then try again."
            )

        # Fall back to Claude (handles tool calls, complex reasoning).
        tools_payload: Any = self.tools.schemas()
        # Use trimmed conversation for context, preserving tool_use/tool_result pairs
        messages_payload: Any = self.conversation.trimmed_for_context(max_messages=20)
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

    @staticmethod
    def _looks_like_self_dialogue(text: str) -> bool:
        if not text:
            return False
        markers = re.findall(
            r"(?im)(?:^|\n)\s*(?:\*\*)?\s*(user|you|jarvis(?:\s*\(me\))?|assistant)\s*[:：]",
            text,
        )
        if len(markers) < 2:
            return False
        roles = {m.lower() for m in markers}
        has_user = any(r in roles for r in {"user", "you"})
        has_assistant = any(r.startswith("jarvis") or r == "assistant" for r in roles)
        return has_user and has_assistant

    @staticmethod
    def _strip_role_prefixes(text: str) -> str:
        if not text:
            return ""
        # Prefer the last assistant segment if the model emitted a transcript.
        parts = re.split(
            r"(?im)(?:^|\n)\s*(?:\*\*)?\s*(?:jarvis(?:\s*\(me\))?|assistant)\s*[:：]\s*",
            text,
        )
        candidate = parts[-1].strip() if len(parts) > 1 else text.strip()
        candidate = re.sub(
            r"(?im)^\s*(?:\*\*)?\s*(?:user|you)\s*[:：].*$",
            "",
            candidate,
        ).strip()
        return candidate

    @classmethod
    def _sanitize_final_text(cls, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return cleaned
        if cls._looks_like_self_dialogue(cleaned):
            cleaned = cls._strip_role_prefixes(cleaned)
            if not cleaned:
                cleaned = (
                    "Understood. I will answer directly as Jarvis only. "
                    "Tell me the exact task and I will execute it."
                )
        return cleaned

    @staticmethod
    def _is_self_dialogue_request(user_input: str) -> bool:
        """Detect explicit requests to run self-dialogue (internal testing mode).
        
        Returns True only for explicit "run self dialogue" requests, not for casual
        questions about dialogue capabilities (e.g., "can you have a dialogue with jarvis").
        
        This guards against regressions where legitimate dialogue questions get 
        intercepted and return canned responses.
        """
        text = (user_input or "").strip().lower()
        if not text:
            return False
        
        # Explicit run/simulate triggers (testing mode)
        explicit_triggers = (
            "run self dialog",
            "run self dialogue",
            "start self dialog",
            "simulate conversation",
            "simulate dialog",
        )
        
        # Reject casual questions that mention dialogue (e.g., "can you have a dialogue")
        if any(phrase in text for phrase in ["can you have", "can i have", "do you support", "how do you", "what about"]):
            return False
        
        return any(t in text for t in explicit_triggers)

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
            return make_error_payload("ERR_POLICY_DENIED", detail=decision.reason)

        tool = self.tools.get(name)
        if not tool:
            return make_error_payload("ERR_TOOL_NOT_FOUND", detail=f"no handler registered for '{name}'")

        result: Any = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                result = tool.handler(**args)
                break
            except TypeError as e:
                result = make_error_payload("ERR_TOOL_BAD_ARGS", detail=str(e))
                break
            except Exception as e:
                if self.retry_policy.should_retry(attempt):
                    continue
                result = make_error_payload("ERR_TOOL_FAILURE", detail=f"{e.__class__.__name__}: {e}")

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
                result = make_error_payload("ERR_INVALID_TOOL_INPUT", detail=f"got {type(raw_input).__name__}")
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
        """One conversational turn. Returns the agent's final text (always a str)."""
        import time

        if self._is_self_dialogue_request(user_input):
            return (
                "I won't run self-dialogue mode. "
                "Give me one concrete task and I will answer directly."
            )

        def _run_turn(t_user_input: str) -> str:
            t_correlation_id = str(uuid4())
            t_turn = self.runtime.start_turn(t_user_input, t_correlation_id)
            self._active_turn = t_turn
            self._perceive(t_turn)

            while not t_turn.exhausted:
                t0 = time.perf_counter()
                response = self._plan(t_turn)
                t1 = time.perf_counter()
                print(f"[DEBUG] LLM API call took {t1-t0:.2f}s")
                self._observe(response, t_correlation_id)

                blocks = self._content_blocks(response)
                has_tool_use = any(getattr(b, "type", None) == "tool_use" for b in blocks)

                if has_tool_use:
                    t2 = time.perf_counter()
                    tool_results = self._dispatch_requested_tools(response, t_turn)
                    t3 = time.perf_counter()
                    print(f"[DEBUG] Tool execution took {t3-t2:.2f}s")
                    t_turn.complete_react_cycle()
                    if tool_results:
                        self.conversation.add_tool_results(tool_results)
                    continue

                final_text = self.runtime.final_text_from_blocks(blocks)
                sanitized = self._sanitize_final_text(final_text)
                if sanitized != final_text:
                    self.conversation.overwrite_last_assistant_text(sanitized)
                return sanitized

            return "(stopped after max iterations — task too long for one turn)"

        try:
            return _run_turn(user_input)
        except ToolResultProtocolError as e:
            self.conversation.reset()
            return f"I had a tool protocol error and reset my memory. Please repeat your request."
        except Exception as e:
            err_str = str(e)
            # Claude 400: dangling tool_use in stored history — reset and retry once
            if "tool_use" in err_str and "tool_result" in err_str:
                print(f"[WARN] Corrupt conversation history detected, resetting: {err_str[:160]}")
                self.conversation.reset()
                try:
                    return _run_turn(user_input)
                except Exception as e2:
                    return f"Sorry, I couldn't recover after resetting memory. Error: {e2}"
            return f"Error: {err_str}"

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
