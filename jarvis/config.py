"""Environment-driven config. Loaded once at startup."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from .secrets import EnvSecretProvider, SecretProvider, build_secret_provider

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw.strip())
        return max(min_val, min(max_val, value))
    except ValueError:
        return default


def _env_int_map(name: str) -> dict[str, int]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}

    result: dict[str, int] = {}
    for part in raw.split(","):
        item = part.strip()
        if not item or ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        try:
            parsed = int(value)
        except ValueError:
            continue
        if parsed > 0:
            result[key] = parsed
    return result


def _env_str_map(name: str) -> dict[str, str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}

    result: dict[str, str] = {}
    for part in raw.split(","):
        item = part.strip()
        if not item or ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _env_csv(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return ()
    parts = [item.strip() for item in raw.split(",")]
    return tuple(item for item in parts if item)


def _default_conversation_store_path() -> Path:
    # Always use D:/jarvis-data for persistent conversation storage
    return Path("D:/jarvis-data/conversation.json")


@dataclass
class Config:
    anthropic_api_key: str
    model: str
    notes_dir: Path
    audit_db: Path
    user_name: str
    conversation_store_path: Path | None = None
    user_preferences_store_path: Path | None = None
    secret_provider: str = "env"
    secret_provider_impl: SecretProvider = field(
        default_factory=EnvSecretProvider,
        repr=False,
    )
    deployment_target: str = "laptop"
    voice_stack: str = "local"
    phase_voice: bool = False
    phase_smart_home: bool = False
    phase_approvals: bool = False
    phase_payments: bool = False
    phase_telephony: bool = False
    phase_trading: bool = False
    phase_sandbox: bool = False
    sandbox_dir: Path = Path("D:/jarvis-data/sandbox")
    sandbox_shell_timeout_seconds: int = 30
    voice_wake_word: str = "jarvis"
    voice_stt_provider: str = "faster-whisper"
    voice_tts_provider: str = "piper"
    voice_tts_api_key: str = ""
    voice_tts_model: str = "eleven_multilingual_v2"
    voice_tts_default_voice: str = "male"
    voice_tts_persona: str = "jarvis"
    voice_tts_voice_id_male: str = ""
    voice_tts_voice_id_female: str = ""
    voice_tts_voice_id_jarvis: str = ""
    voice_tts_voice_id_eva: str = ""
    voice_tts_fallback_provider: str = "piper"
    # Voice personality / soul parameters (ElevenLabs only)
    voice_tts_stability: float = 0.7
    voice_tts_similarity_boost: float = 0.75
    voice_tts_style: float = 0.5
    voice_tts_speaker_boost: bool = True
    mac_pc_pipeline_mode: str = "dry_run"
    mac_pc_pipeline_source_id: str = "mac"
    mac_pc_pipeline_target_id: str = "pc"
    mac_pc_pipeline_target_url: str = ""
    mac_pc_pipeline_shared_secret: str = ""
    location_tools_mode: str = "dry_run"
    gold_market_mode: str = "dry_run"
    news_sentiment_mode: str = "dry_run"
    youtube_sentiment_mode: str = "dry_run"
    home_assistant_url: str = ""
    home_assistant_token: str = ""
    home_assistant_timeout_seconds: int = 10
    telephony_provider: str = "dry_run"
    telephony_caller_id: str = ""
    telephony_vapi_assistant_id: str = ""
    telephony_vapi_phone_number_id: str = ""
    telephony_disclosure_template: str = (
        "Hello, this is an AI assistant calling on behalf of {user_name} "
        "to {purpose}. Is that alright to proceed?"
    )
    message_send_mode: str = "dry_run"
    messaging_primary_channel: str = "sms"
    messaging_fallback_channels: tuple[str, ...] = ("imessage", "slack", "push", "email")
    message_outbox: Path = Path(os.path.expanduser("D:/jarvis-data/message-outbox.jsonl"))
    call_phone_mode: str = "dry_run"
    calls_log_path: Path = Path(os.path.expanduser("D:/jarvis-data/calls-log.jsonl"))
    payments_mode: str = "dry_run"
    payments_ledger: Path = Path(os.path.expanduser("D:/jarvis-data/payments-ledger.jsonl"))
    payments_budget_db: Path = Path(os.path.expanduser("D:/jarvis-data/payments-budget.db"))
    payments_monthly_cap: float = 10000.0
    payments_tx_limit: float = 10000.0
    payments_allowed_mccs: tuple[str, ...] = ()
    payments_webhook_secret: str = ""
    trades_mode: str = "dry_run"
    trades_log: Path = Path(os.path.expanduser("D:/jarvis-data/trades-log.jsonl"))
    trading_account_equity: float = 100000.0
    trading_max_position_pct: float = 2.0
    trading_live_cooldown_seconds: int = 300
    trading_daily_drawdown_kill_pct: float = 5.0
    trading_review_min_trading_days: int = 20
    trading_review_min_trades: int = 100
    trading_review_min_win_rate: float = 0.5
    trading_review_min_profit_factor: float = 1.0
    trading_review_min_avg_r_multiple: float = 0.0
    trading_review_max_anomalies: int = 0
    approval_db: Path = Path(os.path.expanduser("D:/jarvis-data/approvals.db"))
    approvals_ttl_seconds: int = 900
    approvals_dispatch_cooldown_seconds: int = 0
    approvals_dispatch_max_per_run: int = 25
    approvals_dispatch_cooldown_by_kind: dict[str, int] = field(default_factory=dict)
    calendar_ics: Path = Path(os.path.expanduser("D:/jarvis-data/calendar.ics"))
    event_bus_db: Path = Path(os.path.expanduser("D:/jarvis-data/event-bus.db"))
    dropzone_dir: Path = Path(os.path.expanduser("D:/jarvis-data/dropzone"))
    rss_feed_url: str = ""
    webhook_host: str = "127.0.0.1"
    webhook_port: int = 9010
    webhook_source_name: str = "default"
    webhook_secret: str = ""
    webhook_path_kind_map: dict[str, str] = field(default_factory=dict)
    vision_host: str = "127.0.0.1"
    vision_port: int = 9021
    vision_source_name: str = "iphone"
    vision_secret: str = ""
    vision_max_frame_bytes: int = 2000000
    vision_min_face_confidence: float = 0.8
    vision_min_color_coverage: float = 0.8
    event_alert_channel: str = "slack"
    event_alert_recipient: str = "#ops"
    event_alerts_max_per_hour_by_kind: dict[str, int] = field(default_factory=dict)
    event_actions_retention_days: int = 30
    mail_drafts_path: Path = Path(os.path.expanduser("D:/jarvis-data/mail-drafts.jsonl"))
    approvals_api_host: str = "0.0.0.0"
    approvals_api_port: int = 8080
    chat_account_id: str = ""
    chat_auth_token: str = ""
    chat_accounts: dict[str, str] = field(default_factory=dict)
    approval_channel: str = "ntfy"
    ntfy_topic: str = ""
    ntfy_url: str = "https://ntfy.sh"
    ntfy_priority: str = "high"
    ntfy_token: str = ""
    twilio_webhook_token: str = ""
    trading_paper_broker: str = "alpaca"
    helius_api_key: str = ""
    helius_network: str = "mainnet"
    helius_api_url: str = "https://api.helius.xyz"
    mapbox_token: str = ""
    owm_api_key: str = ""
    ollama_enabled: bool = True
    ollama_base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_timeout: int = 45
    ollama_local_only: bool = False
    ollama_warm_model: str = "dolphin3:8b"
    ollama_fast_mode: bool = True
    ollama_num_ctx: int = 8192
    ollama_num_predict: int = 256
    ollama_keep_alive: str = "30m"
    # Anthropic fallback is already handled in brain.py if Ollama fails

    @classmethod
    def from_env(cls) -> "Config":
        secret_provider_name = (
            os.environ.get("JARVIS_SECRET_PROVIDER", "env").strip().lower()
            or "env"
        )
        secret_provider = build_secret_provider(secret_provider_name)

        return cls(
            anthropic_api_key=secret_provider.get("ANTHROPIC_API_KEY"),
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            secret_provider=secret_provider_name,
            secret_provider_impl=secret_provider,
            deployment_target=(
                os.environ.get("JARVIS_DEPLOYMENT_TARGET", "laptop").strip().lower()
                or "laptop"
            ),
            voice_stack=(
                os.environ.get("JARVIS_VOICE_STACK", "local").strip().lower()
                or "local"
            ),
            notes_dir=Path(os.path.expanduser(
                os.environ.get("JARVIS_NOTES_DIR", "D:/jarvis-data/notes")
            )),
            audit_db=Path(os.path.expanduser(
                os.environ.get("JARVIS_AUDIT_DB", "D:/jarvis-data/audit.db")
            )),
            conversation_store_path=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_CONVERSATION_STORE_PATH",
                    str(_default_conversation_store_path()),
                )
            )),
            user_preferences_store_path=Path(os.path.expanduser(
                os.environ.get("JARVIS_USER_PREFERENCES_STORE_PATH", "D:/jarvis-data/preferences.json")
            )),
            user_name=os.environ.get("JARVIS_USER_NAME", "User"),
            phase_voice=_env_bool("JARVIS_PHASE_VOICE", default=False),
            phase_smart_home=_env_bool("JARVIS_PHASE_SMART_HOME", default=False),
            phase_approvals=_env_bool("JARVIS_PHASE_APPROVALS", default=False),
            phase_payments=_env_bool("JARVIS_PHASE_PAYMENTS", default=False),
            phase_telephony=_env_bool("JARVIS_PHASE_TELEPHONY", default=False),
            phase_trading=_env_bool("JARVIS_PHASE_TRADING", default=False),
            phase_sandbox=_env_bool("JARVIS_PHASE_SANDBOX", default=False),
            sandbox_dir=Path(os.path.expanduser(
                os.environ.get("JARVIS_SANDBOX_DIR", "D:/jarvis-data/sandbox")
            )),
            sandbox_shell_timeout_seconds=max(
                1,
                min(
                    int(os.environ.get("JARVIS_SANDBOX_SHELL_TIMEOUT_SECONDS", "30")),
                    60,
                ),
            ),
            voice_wake_word=(
                os.environ.get("JARVIS_VOICE_WAKE_WORD", "jarvis").strip().lower()
                or "jarvis"
            ),
            voice_stt_provider=(
                os.environ.get("JARVIS_VOICE_STT_PROVIDER", "faster-whisper").strip().lower()
                or "faster-whisper"
            ),
            voice_tts_provider=(
                os.environ.get("JARVIS_VOICE_TTS_PROVIDER", "piper").strip().lower()
                or "piper"
            ),
            voice_tts_api_key=secret_provider.get("ELEVENLABS_API_KEY").strip(),
            voice_tts_model=(
                os.environ.get("JARVIS_VOICE_TTS_MODEL", "eleven_multilingual_v2").strip()
                or "eleven_multilingual_v2"
            ),
            voice_tts_default_voice=(
                os.environ.get("JARVIS_VOICE_TTS_DEFAULT_VOICE", "male").strip().lower()
                or "male"
            ),
            voice_tts_persona=(
                os.environ.get("JARVIS_VOICE_TTS_PERSONA", "jarvis").strip().lower()
                or "jarvis"
            ),
            voice_tts_voice_id_male=os.environ.get("JARVIS_VOICE_TTS_VOICE_ID_MALE", "").strip(),
            voice_tts_voice_id_female=os.environ.get("JARVIS_VOICE_TTS_VOICE_ID_FEMALE", "").strip(),
            voice_tts_voice_id_jarvis=os.environ.get("JARVIS_VOICE_TTS_VOICE_ID_JARVIS", "").strip(),
            voice_tts_voice_id_eva=os.environ.get("JARVIS_VOICE_TTS_VOICE_ID_EVA", "").strip(),
            voice_tts_fallback_provider=(
                os.environ.get("JARVIS_VOICE_TTS_FALLBACK_PROVIDER", "piper").strip().lower()
                or "piper"
            ),
            voice_tts_stability=_env_float("JARVIS_VOICE_TTS_STABILITY", 0.7, 0.0, 1.0),
            voice_tts_similarity_boost=_env_float("JARVIS_VOICE_TTS_SIMILARITY_BOOST", 0.75, 0.0, 1.0),
            voice_tts_style=_env_float("JARVIS_VOICE_TTS_STYLE", 0.5, 0.0, 1.0),
            voice_tts_speaker_boost=_env_bool("JARVIS_VOICE_TTS_SPEAKER_BOOST", True),
            mac_pc_pipeline_mode=(
                os.environ.get("JARVIS_MAC_PC_PIPELINE_MODE", "dry_run").strip().lower()
                or "dry_run"
            ),
            mac_pc_pipeline_source_id=(
                os.environ.get("JARVIS_MAC_PC_PIPELINE_SOURCE_ID", "mac").strip()
                or "mac"
            ),
            mac_pc_pipeline_target_id=(
                os.environ.get("JARVIS_MAC_PC_PIPELINE_TARGET_ID", "pc").strip()
                or "pc"
            ),
            mac_pc_pipeline_target_url=os.environ.get("JARVIS_MAC_PC_PIPELINE_TARGET_URL", "").strip(),
            mac_pc_pipeline_shared_secret=secret_provider.get("JARVIS_MAC_PC_PIPELINE_SHARED_SECRET").strip(),
            location_tools_mode=(
                os.environ.get("JARVIS_LOCATION_TOOLS_MODE", "dry_run").strip().lower()
                or "dry_run"
            ),
            gold_market_mode=(
                os.environ.get("JARVIS_GOLD_MARKET_MODE", "dry_run").strip().lower()
                or "dry_run"
            ),
            news_sentiment_mode=(
                os.environ.get("JARVIS_NEWS_SENTIMENT_MODE", "dry_run").strip().lower()
                or "dry_run"
            ),
            youtube_sentiment_mode=(
                os.environ.get("JARVIS_YOUTUBE_SENTIMENT_MODE", "dry_run").strip().lower()
                or "dry_run"
            ),
            home_assistant_url=os.environ.get("JARVIS_HOME_ASSISTANT_URL", "").strip(),
            home_assistant_token=secret_provider.get("JARVIS_HOME_ASSISTANT_TOKEN").strip(),
            home_assistant_timeout_seconds=max(
                1,
                int(os.environ.get("JARVIS_HOME_ASSISTANT_TIMEOUT_SECONDS", "10")),
            ),
            telephony_provider=(
                os.environ.get("JARVIS_TELEPHONY_PROVIDER", "dry_run").strip().lower()
                or "dry_run"
            ),
            telephony_caller_id=os.environ.get("JARVIS_TELEPHONY_CALLER_ID", "").strip(),
            telephony_vapi_assistant_id=os.environ.get("JARVIS_TELEPHONY_VAPI_ASSISTANT_ID", "").strip(),
            telephony_vapi_phone_number_id=os.environ.get("JARVIS_TELEPHONY_VAPI_PHONE_NUMBER_ID", "").strip(),
            telephony_disclosure_template=(
                os.environ.get(
                    "JARVIS_TELEPHONY_DISCLOSURE_TEMPLATE",
                    "Hello, this is an AI assistant calling on behalf of {user_name} "
                    "to {purpose}. Is that alright to proceed?",
                ).strip()
                or "Hello, this is an AI assistant calling on behalf of {user_name} to {purpose}. Is that alright to proceed?"
            ),
            message_send_mode=os.environ.get("JARVIS_MESSAGE_SEND_MODE", "dry_run"),
            messaging_primary_channel=(
                os.environ.get("JARVIS_MESSAGING_PRIMARY_CHANNEL", "sms").strip().lower()
                or "sms"
            ),
            messaging_fallback_channels=_env_csv("JARVIS_MESSAGING_FALLBACK_CHANNELS")
            or ("imessage", "slack", "push", "email"),
            message_outbox=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_MESSAGE_OUTBOX",
                    "D:/jarvis-data/message-outbox.jsonl",
                )
            )),
            call_phone_mode=os.environ.get("JARVIS_CALL_PHONE_MODE", "dry_run"),
            calls_log_path=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_CALLS_LOG_PATH",
                    "D:/jarvis-data/calls-log.jsonl",
                )
            )),
            payments_mode=os.environ.get("JARVIS_PAYMENTS_MODE", "dry_run"),
            payments_ledger=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_PAYMENTS_LEDGER",
                    "D:/jarvis-data/payments-ledger.jsonl",
                )
            )),
            payments_budget_db=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_PAYMENTS_BUDGET_DB",
                    "D:/jarvis-data/payments-budget.db",
                )
            )),
            payments_monthly_cap=max(
                0.01,
                float(os.environ.get("JARVIS_PAYMENTS_MONTHLY_CAP", "10000")),
            ),
            payments_tx_limit=max(
                0.01,
                float(os.environ.get("JARVIS_PAYMENTS_TX_LIMIT", "10000")),
            ),
            payments_allowed_mccs=_env_csv("JARVIS_PAYMENTS_ALLOWED_MCCS"),
            payments_webhook_secret=(
                secret_provider.get("JARVIS_PAYMENTS_WEBHOOK_SECRET")
                or secret_provider.get("STRIPE_WEBHOOK_SECRET")
                or os.environ.get("JARVIS_PAYMENTS_WEBHOOK_SECRET", "")
            ).strip(),
            trades_mode=os.environ.get("JARVIS_TRADES_MODE", "dry_run"),
            trades_log=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_TRADES_LOG",
                    "D:/jarvis-data/trades-log.jsonl",
                )
            )),
            trading_account_equity=max(
                0.0,
                float(os.environ.get("JARVIS_TRADING_ACCOUNT_EQUITY", "100000")),
            ),
            trading_max_position_pct=max(
                0.0,
                float(os.environ.get("JARVIS_TRADING_MAX_POSITION_PCT", "2.0")),
            ),
            trading_live_cooldown_seconds=max(
                0,
                int(os.environ.get("JARVIS_TRADING_LIVE_COOLDOWN_SECONDS", "300")),
            ),
            trading_daily_drawdown_kill_pct=max(
                0.0,
                float(os.environ.get("JARVIS_TRADING_DAILY_DRAWDOWN_KILL_PCT", "5.0")),
            ),
            trading_review_min_trading_days=max(
                1,
                int(os.environ.get("JARVIS_TRADING_REVIEW_MIN_TRADING_DAYS", "20")),
            ),
            trading_review_min_trades=max(
                1,
                int(os.environ.get("JARVIS_TRADING_REVIEW_MIN_TRADES", "100")),
            ),
            trading_review_min_win_rate=max(
                0.0,
                min(1.0, float(os.environ.get("JARVIS_TRADING_REVIEW_MIN_WIN_RATE", "0.5"))),
            ),
            trading_review_min_profit_factor=max(
                0.0,
                float(os.environ.get("JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR", "1.0")),
            ),
            trading_review_min_avg_r_multiple=float(
                os.environ.get("JARVIS_TRADING_REVIEW_MIN_AVG_R_MULTIPLE", "0.0")
            ),
            trading_review_max_anomalies=max(
                0,
                int(os.environ.get("JARVIS_TRADING_REVIEW_MAX_ANOMALIES", "0")),
            ),
            approval_db=Path(os.path.expanduser(
                os.environ.get("JARVIS_APPROVAL_DB", "D:/jarvis-data/approvals.db")
            )),
            approvals_ttl_seconds=int(
                os.environ.get("JARVIS_APPROVALS_TTL_SECONDS", "900")
            ),
            approvals_dispatch_cooldown_seconds=int(
                os.environ.get("JARVIS_APPROVALS_DISPATCH_COOLDOWN_SECONDS", "0")
            ),
            approvals_dispatch_max_per_run=int(
                os.environ.get("JARVIS_APPROVALS_DISPATCH_MAX_PER_RUN", "25")
            ),
            approvals_dispatch_cooldown_by_kind=_env_int_map(
                "JARVIS_APPROVALS_DISPATCH_COOLDOWN_BY_KIND"
            ),
            calendar_ics=Path(os.path.expanduser(
                os.environ.get("JARVIS_CALENDAR_ICS", "D:/jarvis-data/calendar.ics")
            )),
            event_bus_db=Path(os.path.expanduser(
                os.environ.get("JARVIS_EVENT_BUS_DB", "D:/jarvis-data/event-bus.db")
            )),
            dropzone_dir=Path(os.path.expanduser(
                os.environ.get("JARVIS_DROPZONE_DIR", "D:/jarvis-data/dropzone")
            )),
            rss_feed_url=os.environ.get("JARVIS_RSS_FEED_URL", "").strip(),
            webhook_host=os.environ.get("JARVIS_WEBHOOK_HOST", "127.0.0.1").strip(),
            webhook_port=int(os.environ.get("JARVIS_WEBHOOK_PORT", "9010")),
            webhook_source_name=(
                os.environ.get("JARVIS_WEBHOOK_SOURCE", "default").strip()
                or "default"
            ),
            webhook_secret=secret_provider.get("JARVIS_WEBHOOK_SECRET"),
            webhook_path_kind_map=_env_str_map("JARVIS_WEBHOOK_PATH_KIND_MAP"),
            vision_host=os.environ.get("JARVIS_VISION_HOST", "127.0.0.1").strip(),
            vision_port=int(os.environ.get("JARVIS_VISION_PORT", "9021")),
            vision_source_name=(
                os.environ.get("JARVIS_VISION_SOURCE", "iphone").strip() or "iphone"
            ),
            vision_secret=secret_provider.get("JARVIS_VISION_SECRET"),
            vision_max_frame_bytes=max(
                1024,
                int(os.environ.get("JARVIS_VISION_MAX_FRAME_BYTES", "2000000")),
            ),
            vision_min_face_confidence=_env_float(
                "JARVIS_VISION_MIN_FACE_CONFIDENCE", default=0.8, min_val=0.0, max_val=1.0
            ),
            vision_min_color_coverage=_env_float(
                "JARVIS_VISION_MIN_COLOR_COVERAGE", default=0.8, min_val=0.0, max_val=1.0
            ),
            event_alert_channel=(
                os.environ.get("JARVIS_EVENT_ALERT_CHANNEL", "slack").strip().lower()
                or "slack"
            ),
            event_alert_recipient=(
                os.environ.get("JARVIS_EVENT_ALERT_RECIPIENT", "#ops").strip()
                or "#ops"
            ),
            event_alerts_max_per_hour_by_kind=_env_int_map(
                "JARVIS_EVENT_ALERTS_MAX_PER_HOUR_BY_KIND"
            ),
            event_actions_retention_days=max(
                1,
                int(os.environ.get("JARVIS_EVENT_ACTIONS_RETENTION_DAYS", "30")),
            ),
            mail_drafts_path=Path(os.path.expanduser(
                os.environ.get(
                    "JARVIS_MAIL_DRAFTS_PATH",
                    "D:/jarvis-data/mail-drafts.jsonl",
                )
            )),
            approvals_api_host=os.environ.get("JARVIS_APPROVALS_API_HOST", "0.0.0.0"),
            approvals_api_port=int(os.environ.get("JARVIS_APPROVALS_API_PORT", "8080")),
            chat_account_id=(
                os.environ.get("JARVIS_CHAT_ACCOUNT_ID", "").strip().lower()
            ),
            chat_auth_token=(
                secret_provider.get("JARVIS_CHAT_AUTH_TOKEN")
                or os.environ.get("JARVIS_CHAT_AUTH_TOKEN", "")
            ).strip(),
            chat_accounts=_env_str_map("JARVIS_CHAT_ACCOUNTS"),
            approval_channel=(
                os.environ.get("JARVIS_APPROVAL_CHANNEL", "ntfy").strip().lower()
                or "ntfy"
            ),
            ntfy_topic=os.environ.get("JARVIS_NTFY_TOPIC", "").strip(),
            ntfy_url=(
                os.environ.get("JARVIS_NTFY_URL", "https://ntfy.sh").strip()
                or "https://ntfy.sh"
            ),
            ntfy_priority=(
                os.environ.get("JARVIS_NTFY_PRIORITY", "high").strip()
                or "high"
            ),
            ntfy_token=os.environ.get("JARVIS_NTFY_TOKEN", "").strip(),
            twilio_webhook_token=(
                secret_provider.get("JARVIS_TWILIO_WEBHOOK_TOKEN")
                or os.environ.get("JARVIS_TWILIO_WEBHOOK_TOKEN", "")
            ).strip(),
            trading_paper_broker=(
                os.environ.get("JARVIS_TRADING_PAPER_BROKER", "alpaca").strip().lower()
                or "alpaca"
            ),
            helius_api_key=secret_provider.get("HELIUS_API_KEY"),
            helius_network=os.environ.get("HELIUS_NETWORK", "mainnet"),
            mapbox_token=os.environ.get("MAPBOX_TOKEN", "").strip(),
            owm_api_key=os.environ.get("OWM_API_KEY", "").strip(),
            ollama_enabled=_env_bool("JARVIS_OLLAMA_ENABLED", default=True),
            ollama_base_url=os.environ.get("JARVIS_OLLAMA_BASE_URL", "http://localhost:11434").strip(),
            ollama_timeout=max(10, int(os.environ.get("JARVIS_OLLAMA_TIMEOUT", "45"))),
            ollama_local_only=_env_bool("JARVIS_OLLAMA_LOCAL_ONLY", default=False),
            ollama_warm_model=(
                os.environ.get("JARVIS_OLLAMA_WARM_MODEL", "dolphin3:8b").strip()
                or "dolphin3:8b"
            ),
            ollama_fast_mode=_env_bool("JARVIS_OLLAMA_FAST_MODE", default=True),
            ollama_num_ctx=max(1024, int(os.environ.get("JARVIS_OLLAMA_NUM_CTX", "8192"))),
            ollama_num_predict=max(64, int(os.environ.get("JARVIS_OLLAMA_NUM_PREDICT", "256"))),
            ollama_keep_alive=(
                os.environ.get("JARVIS_OLLAMA_KEEP_ALIVE", "30m").strip()
                or "30m"
            ),
        )

    def phase_enabled(self, phase: str) -> bool:
        """Return True if the named phase flag is currently enabled.

        Valid phase names: ``voice``, ``smart_home``, ``approvals``,
        ``payments``, ``telephony``, ``trading``.
        """
        return phase in self.enabled_phases()

    def get_secret(self, key: str) -> str:
        """Fetch secret values from the configured provider at call-time."""
        value = self.secret_provider_impl.get(key)
        return (value or "").strip()

    def enabled_phases(self) -> set[str]:
        enabled = set()
        if self.phase_voice:
            enabled.add("voice")
        if self.phase_smart_home:
            enabled.add("smart_home")
        if self.phase_approvals:
            enabled.add("approvals")
        if self.phase_payments:
            enabled.add("payments")
        if self.phase_telephony:
            enabled.add("telephony")
        if self.phase_trading:
            enabled.add("trading")
        if self.phase_sandbox:
            enabled.add("sandbox")
        return enabled

    def validate(self) -> None:
        anthropic_key = self.get_secret("ANTHROPIC_API_KEY") or self.anthropic_api_key
        if not anthropic_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Copy .env.example to .env and fill it in."
            )

        phase_dependency_errors: list[str] = []
        if self.phase_payments and not self.phase_approvals:
            phase_dependency_errors.append(
                "JARVIS_PHASE_PAYMENTS requires JARVIS_PHASE_APPROVALS=true"
            )
        if self.phase_telephony and not self.phase_approvals:
            phase_dependency_errors.append(
                "JARVIS_PHASE_TELEPHONY requires JARVIS_PHASE_APPROVALS=true"
            )
        if self.phase_trading and not self.phase_approvals:
            phase_dependency_errors.append(
                "JARVIS_PHASE_TRADING requires JARVIS_PHASE_APPROVALS=true"
            )

        if self.phase_voice:
            if not self.voice_wake_word.strip():
                phase_dependency_errors.append(
                    "JARVIS_PHASE_VOICE requires JARVIS_VOICE_WAKE_WORD"
                )
            if not self.voice_stt_provider.strip():
                phase_dependency_errors.append(
                    "JARVIS_PHASE_VOICE requires JARVIS_VOICE_STT_PROVIDER"
                )
            if not self.voice_tts_provider.strip():
                phase_dependency_errors.append(
                    "JARVIS_PHASE_VOICE requires JARVIS_VOICE_TTS_PROVIDER"
                )
            if self.voice_tts_default_voice not in {"male", "female"}:
                phase_dependency_errors.append(
                    "JARVIS_PHASE_VOICE requires JARVIS_VOICE_TTS_DEFAULT_VOICE to be 'male' or 'female'"
                )
            if self.voice_tts_provider == "elevenlabs":
                if not self.voice_tts_api_key.strip():
                    phase_dependency_errors.append(
                        "JARVIS_VOICE_TTS_PROVIDER=elevenlabs requires ELEVENLABS_API_KEY"
                    )
                if not self.voice_tts_voice_id_male.strip():
                    phase_dependency_errors.append(
                        "JARVIS_VOICE_TTS_PROVIDER=elevenlabs requires JARVIS_VOICE_TTS_VOICE_ID_MALE"
                    )
                if not self.voice_tts_voice_id_female.strip():
                    phase_dependency_errors.append(
                        "JARVIS_VOICE_TTS_PROVIDER=elevenlabs requires JARVIS_VOICE_TTS_VOICE_ID_FEMALE"
                    )

        if self.phase_smart_home:
            if not self.home_assistant_url.strip():
                phase_dependency_errors.append(
                    "JARVIS_PHASE_SMART_HOME requires JARVIS_HOME_ASSISTANT_URL"
                )
            if not self.home_assistant_token.strip():
                phase_dependency_errors.append(
                    "JARVIS_PHASE_SMART_HOME requires JARVIS_HOME_ASSISTANT_TOKEN"
                )

        if self.phase_telephony and not self.telephony_caller_id.strip():
            phase_dependency_errors.append(
                "JARVIS_PHASE_TELEPHONY requires JARVIS_TELEPHONY_CALLER_ID"
            )
        if self.phase_telephony:
            provider = self.telephony_provider.strip().lower()
            if provider not in {"dry_run", "twilio", "vapi"}:
                phase_dependency_errors.append(
                    "JARVIS_TELEPHONY_PROVIDER must be one of: dry_run, twilio, vapi"
                )
            if provider == "vapi":
                if not self.get_secret("VAPI_API_KEY"):
                    phase_dependency_errors.append(
                        "JARVIS_TELEPHONY_PROVIDER=vapi requires VAPI_API_KEY"
                    )
                if not self.telephony_vapi_assistant_id.strip():
                    phase_dependency_errors.append(
                        "JARVIS_TELEPHONY_PROVIDER=vapi requires JARVIS_TELEPHONY_VAPI_ASSISTANT_ID"
                    )
                if not self.telephony_vapi_phone_number_id.strip():
                    phase_dependency_errors.append(
                        "JARVIS_TELEPHONY_PROVIDER=vapi requires JARVIS_TELEPHONY_VAPI_PHONE_NUMBER_ID"
                    )
        if phase_dependency_errors:
            raise ValueError("; ".join(phase_dependency_errors))

        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.audit_db.parent.mkdir(parents=True, exist_ok=True)
        self.message_outbox.parent.mkdir(parents=True, exist_ok=True)
        self.calls_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.payments_ledger.parent.mkdir(parents=True, exist_ok=True)
        self.payments_budget_db.parent.mkdir(parents=True, exist_ok=True)
        self.trades_log.parent.mkdir(parents=True, exist_ok=True)
        self.event_bus_db.parent.mkdir(parents=True, exist_ok=True)
        self.dropzone_dir.mkdir(parents=True, exist_ok=True)
        self.approval_db.parent.mkdir(parents=True, exist_ok=True)
        self.mail_drafts_path.parent.mkdir(parents=True, exist_ok=True)
