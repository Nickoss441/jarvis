"""
Ollama LLM Adapter and Model Router for Jarvis.

Routing logic:
  trading/financial keywords  → deepseek-r1:7b  (careful step-by-step reasoning)
  coding keywords             → qwen2.5:14b      (best local coder)
  everything else             → dolphin3:8b      (fast, uncensored default)

If Ollama is unreachable or returns an error the router returns None and
Brain falls back to Claude transparently.
"""
import logging
import requests
import time as _time

logger = logging.getLogger(__name__)

_TRADING_KEYWORDS = {
    "trade", "buy", "sell", "stock", "crypto", "bitcoin", "btc", "eth",
    "price", "market", "position", "risk", "portfolio", "equity", "profit",
    "loss", "order", "alpaca", "broker", "drawdown", "hedge", "volatility",
    "signal", "short", "long", "option", "futures", "forex", "coin",
}

_CODING_KEYWORDS = {
    "code", "function", "class", "debug", "implement", "script", "bug",
    "error", "refactor", "test", "api", "endpoint", "import", "python",
    "javascript", "typescript", "def ", "fix the", "write a",
}

_LIVE_DATA_KEYWORDS = {
    "weather", "temperature", "forecast", "rain", "wind",
    "price", "stock", "btc", "bitcoin", "gold", "oil", "market",
    "news", "latest", "today", "now", "current", "live",
    "calendar", "event", "schedule", "email", "send", "message",
    "approval", "approve", "reject", "status",
}

_INCOMPLETE_RESPONSE_MARKERS = (
    "please wait",
    "one moment",
    "fetching",
    "i will find",
    "i'll find",
    "let me check",
    "checking",
    "retrieving",
    "loading",
)

DEFAULT_MODEL   = "dolphin3:8b"
REASONING_MODEL = "deepseek-r1:7b"
CODER_MODEL     = "qwen2.5:7b"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_RETRIES = 1
RETRY_BACKOFF_SECONDS = 0.35


def _pick_model(text: str, fast_mode: bool = False) -> str:
    if fast_mode:
        # Force the fastest local path by default.
        return DEFAULT_MODEL
    lower = text.lower()
    if any(k in lower for k in _TRADING_KEYWORDS):
        return REASONING_MODEL
    if any(k in lower for k in _CODING_KEYWORDS):
        return CODER_MODEL
    return DEFAULT_MODEL


def _looks_incomplete_response(text: str) -> bool:
    lower = text.strip().lower()
    if not lower:
        return True
    return any(marker in lower for marker in _INCOMPLETE_RESPONSE_MARKERS)


def _to_ollama_messages(messages: list) -> list[dict]:
    """Convert Anthropic-format messages to Ollama chat format."""
    result = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # Flatten content blocks to plain text
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        parts.append(str(block.get("content", "")))
                else:
                    parts.append(str(block))
            content = " ".join(p for p in parts if p).strip()
        if content:
            result.append({"role": role, "content": content})
    return result


class OllamaModelRouter:
    """Routes to the best local model; returns None on any failure."""

    # Cache availability check for 60s to avoid a network call every turn
    _avail_cache: bool | None = None
    _avail_checked_at: float = 0.0
    _AVAIL_TTL = 60.0
    # Cache which models are actually loaded
    _loaded_models: set[str] = set()

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        retry_backoff_seconds: float = RETRY_BACKOFF_SECONDS,
        fast_mode: bool = True,
        num_ctx: int = 8192,
        num_predict: int = 256,
        keep_alive: str = "30m",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self.fast_mode = bool(fast_mode)
        self.num_ctx = max(1024, int(num_ctx))
        self.num_predict = max(32, int(num_predict))
        self.keep_alive = keep_alive or "30m"

    def available(self) -> bool:
        now = _time.monotonic()
        if OllamaModelRouter._avail_cache is not None and (now - OllamaModelRouter._avail_checked_at) < OllamaModelRouter._AVAIL_TTL:
            return OllamaModelRouter._avail_cache
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if r.status_code == 200:
                models = r.json().get("models", [])
                OllamaModelRouter._loaded_models = {m["name"] for m in models if "name" in m}
                OllamaModelRouter._avail_cache = bool(OllamaModelRouter._loaded_models)
            else:
                OllamaModelRouter._avail_cache = False
        except Exception:
            OllamaModelRouter._avail_cache = False
        OllamaModelRouter._avail_checked_at = now
        return bool(OllamaModelRouter._avail_cache)

    def _best_available_model(self, preferred: str) -> str | None:
        """Return preferred model if loaded, else any loaded model, else None."""
        loaded = OllamaModelRouter._loaded_models
        if not loaded:
            return None
        # Exact match
        if preferred in loaded:
            return preferred
        # Prefix match (e.g. "llama2" matches "llama2:latest")
        base = preferred.split(":")[0]
        for m in sorted(loaded):
            if m.split(":")[0] == base:
                return m
        # Fallback: return whatever is loaded
        return next(iter(sorted(loaded)))

    def warm_load(self, preferred_model: str = "") -> bool:
        """Best-effort model warm-load to reduce first-turn latency/failures."""
        if not self.available():
            logger.warning("Ollama warm-load skipped: service unavailable")
            return False

        target = None
        if preferred_model:
            target = self._best_available_model(preferred_model)
        if not target:
            target = self._best_available_model(DEFAULT_MODEL)
        if not target:
            logger.warning("Ollama warm-load skipped: no loaded models")
            return False

        try:
            # Tiny prompt to force model into memory/cache.
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": target,
                    "prompt": "ok",
                    "stream": False,
                    "keep_alive": self.keep_alive,
                    "options": {
                        "num_ctx": self.num_ctx,
                        "num_predict": 16,
                    },
                },
                timeout=min(self.timeout, 12),
            )
            resp.raise_for_status()
            logger.info("Ollama warm-loaded model: %s", target)
            return True
        except Exception as exc:
            logger.warning("Ollama warm-load failed for %s: %s", target, exc)
            return False

    def chat(self, messages: list, system: str | None = None) -> str | None:
        """
        Try Ollama chat with the best model for this request.
        Returns response text, or None if Ollama is unavailable / errors.
        """
        user_text = " ".join(
            m.get("content", "") if isinstance(m.get("content"), str)
            else " ".join(
                b.get("text", "") for b in m.get("content", [])
                if isinstance(b, dict) and b.get("type") == "text"
            )
            for m in messages if m.get("role") == "user"
        )

        preferred = _pick_model(user_text, fast_mode=self.fast_mode)
        model = self._best_available_model(preferred)
        if not model:
            return None

        payload_messages = []
        if system:
            # Send a lean version of the system prompt to Ollama (skip tool inventory)
            import re as _re
            lean = _re.sub(r"<tool_families>[\s\S]*?</tool_families>", "", system, flags=_re.DOTALL).strip()
            payload_messages.append({"role": "system", "content": lean})
        payload_messages.extend(_to_ollama_messages(messages))

        attempts = self.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": payload_messages,
                        "stream": False,
                        "keep_alive": self.keep_alive,
                        "options": {
                            "num_ctx": self.num_ctx,
                            "num_predict": self.num_predict,
                        },
                    },
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                text = resp.json().get("message", {}).get("content", "").strip()
                if text:
                    # Avoid returning placeholder/progress text that never gets a
                    # follow-up in non-streaming mode.
                    if _looks_incomplete_response(text):
                        logger.info("Ollama returned incomplete placeholder text; forcing final answer")
                        forced_messages = payload_messages + [
                            {
                                "role": "user",
                                "content": (
                                    "Return one final direct answer now. "
                                    "Do not say 'fetching', 'please wait', or that you will check later."
                                ),
                            }
                        ]
                        forced_resp = requests.post(
                            f"{self.base_url}/api/chat",
                            json={
                                "model": model,
                                "messages": forced_messages,
                                "stream": False,
                                "keep_alive": self.keep_alive,
                                "options": {
                                    "num_ctx": self.num_ctx,
                                    "num_predict": self.num_predict,
                                },
                            },
                            timeout=self.timeout,
                        )
                        forced_resp.raise_for_status()
                        forced_text = forced_resp.json().get("message", {}).get("content", "").strip()
                        if forced_text and not _looks_incomplete_response(forced_text):
                            return forced_text
                        return None
                    logger.debug("Ollama (%s) handled request on attempt %d/%d", model, attempt, attempts)
                    return text
                if attempt < attempts:
                    logger.warning(
                        "Ollama returned empty content (%s), retrying attempt %d/%d",
                        model,
                        attempt + 1,
                        attempts,
                    )
                    _time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                logger.warning("Ollama returned empty content (%s), falling back to Claude", model)
                return None
            except requests.RequestException as exc:
                if attempt < attempts:
                    logger.warning(
                        "Ollama request failed (%s), retrying attempt %d/%d: %s",
                        model,
                        attempt + 1,
                        attempts,
                        exc,
                    )
                    _time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                logger.warning("Ollama unavailable (%s) - falling back to Claude", exc)
                return None
            except Exception as exc:
                logger.warning("Ollama unexpected error (%s) - falling back to Claude", exc)
                return None


# ── Legacy single-model adapter (kept for backwards compat) ──────────────────

class OllamaLLMAdapter:
    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt, system=None, stream=False, **kwargs):
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": stream}
        if system:
            payload["system"] = system
        payload.update(kwargs)
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["response"] if "response" in data else data
