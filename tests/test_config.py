from pathlib import Path

from jarvis.config import Config


def test_config_feature_flags_default_false(monkeypatch):
    monkeypatch.delenv("JARVIS_DEPLOYMENT_TARGET", raising=False)
    monkeypatch.delenv("JARVIS_VOICE_STACK", raising=False)
    monkeypatch.delenv("JARVIS_PHASE_VOICE", raising=False)
    monkeypatch.delenv("JARVIS_PHASE_PAYMENTS", raising=False)

    config = Config.from_env()

    assert config.deployment_target == "laptop"
    assert config.voice_stack == "local"
    assert not config.phase_voice
    assert not config.phase_payments


def test_config_feature_flags_parse_truthy(monkeypatch):
    monkeypatch.setenv("JARVIS_DEPLOYMENT_TARGET", "VPS")
    monkeypatch.setenv("JARVIS_VOICE_STACK", "CLOUD")
    monkeypatch.setenv("JARVIS_PHASE_VOICE", "true")
    monkeypatch.setenv("JARVIS_PHASE_APPROVALS", "1")
    monkeypatch.setenv("JARVIS_PHASE_TRADING", "YES")
    monkeypatch.setenv("JARVIS_TWILIO_WEBHOOK_TOKEN", "twilio-bridge-token")

    config = Config.from_env()

    assert config.deployment_target == "vps"
    assert config.voice_stack == "cloud"
    assert config.phase_voice
    assert config.phase_approvals
    assert config.phase_trading
    assert config.twilio_webhook_token == "twilio-bridge-token"


def test_enabled_phases_returns_active_phase_names(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_voice=True,
        phase_smart_home=False,
        phase_approvals=True,
        phase_payments=False,
        phase_telephony=True,
        phase_trading=False,
    )

    assert config.enabled_phases() == {"voice", "approvals", "telephony"}


def test_message_send_config_defaults(monkeypatch):
    monkeypatch.delenv("JARVIS_MESSAGE_SEND_MODE", raising=False)
    monkeypatch.delenv("JARVIS_MESSAGE_OUTBOX", raising=False)
    monkeypatch.delenv("JARVIS_APPROVAL_CHANNEL", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_PAPER_BROKER", raising=False)
    monkeypatch.delenv("JARVIS_PAYMENTS_MONTHLY_CAP", raising=False)
    monkeypatch.delenv("JARVIS_PAYMENTS_TX_LIMIT", raising=False)
    monkeypatch.delenv("JARVIS_PAYMENTS_ALLOWED_MCCS", raising=False)
    monkeypatch.delenv("JARVIS_PAYMENTS_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("JARVIS_PAYMENTS_BUDGET_DB", raising=False)
    monkeypatch.delenv("JARVIS_NOTES_DIR", raising=False)
    monkeypatch.delenv("JARVIS_AUDIT_DB", raising=False)
    monkeypatch.delenv("JARVIS_APPROVAL_DB", raising=False)
    monkeypatch.delenv("JARVIS_EVENT_BUS_DB", raising=False)
    monkeypatch.delenv("JARVIS_DROPZONE_DIR", raising=False)
    monkeypatch.delenv("JARVIS_TRADES_LOG", raising=False)
    monkeypatch.delenv("JARVIS_MAIL_DRAFTS_PATH", raising=False)
    monkeypatch.delenv("JARVIS_CALENDAR_ICS", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_REVIEW_MIN_WIN_RATE", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_REVIEW_MIN_AVG_R_MULTIPLE", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_REVIEW_MAX_ANOMALIES", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_REVIEW_MIN_TRADING_DAYS", raising=False)
    monkeypatch.delenv("JARVIS_TRADING_REVIEW_MIN_TRADES", raising=False)

    config = Config.from_env()

    assert config.message_send_mode == "dry_run"
    assert config.messaging_primary_channel == "sms"
    assert config.messaging_fallback_channels == ("imessage", "slack", "push", "email")
    assert str(config.message_outbox).endswith(".jarvis/message-outbox.jsonl")
    assert config.approval_channel == "ntfy"
    assert config.trading_paper_broker == "alpaca"
    assert config.voice_wake_word == "jarvis"
    assert config.voice_stt_provider == "faster-whisper"
    assert config.voice_tts_provider == "piper"
    assert config.voice_tts_model == "eleven_multilingual_v2"
    assert config.voice_tts_default_voice == "male"
    assert config.voice_tts_voice_id_male == ""
    assert config.voice_tts_voice_id_female == ""
    assert config.voice_tts_fallback_provider == "piper"
    assert config.mac_pc_pipeline_mode == "dry_run"
    assert config.mac_pc_pipeline_source_id == "mac"
    assert config.mac_pc_pipeline_target_id == "pc"
    assert config.mac_pc_pipeline_target_url == ""
    assert config.mac_pc_pipeline_shared_secret == ""
    assert config.location_tools_mode == "dry_run"
    assert config.gold_market_mode == "dry_run"
    assert config.news_sentiment_mode == "dry_run"
    assert config.home_assistant_url == ""
    assert config.home_assistant_token == ""
    assert config.home_assistant_timeout_seconds == 10
    assert config.telephony_provider == "dry_run"
    assert config.telephony_caller_id == ""
    assert config.payments_monthly_cap == 10000.0
    assert config.payments_tx_limit == 10000.0
    assert config.payments_allowed_mccs == ()
    assert str(config.payments_budget_db).endswith(".jarvis/payments-budget.db")
    assert config.payments_webhook_secret == ""
    assert config.trading_account_equity == 100000.0
    assert config.trading_max_position_pct == 2.0
    assert config.trading_live_cooldown_seconds == 300
    assert config.trading_daily_drawdown_kill_pct == 5.0
    assert config.trading_review_min_trading_days == 20
    assert config.trading_review_min_trades == 100
    assert config.trading_review_min_win_rate == 0.5
    assert config.trading_review_min_profit_factor == 1.0
    assert config.trading_review_min_avg_r_multiple == 0.0
    assert config.trading_review_max_anomalies == 0


def test_message_send_config_from_env(monkeypatch, tmp_path):
    outbox = tmp_path / "messages.jsonl"
    approvals = tmp_path / "approvals.db"
    calendar = tmp_path / "calendar.ics"
    drafts = tmp_path / "mail-drafts.jsonl"
    monkeypatch.setenv("JARVIS_MESSAGE_SEND_MODE", "dry_run")
    monkeypatch.setenv("JARVIS_MESSAGING_PRIMARY_CHANNEL", "slack")
    monkeypatch.setenv("JARVIS_MESSAGING_FALLBACK_CHANNELS", "sms,push,email")
    monkeypatch.setenv("JARVIS_MESSAGE_OUTBOX", str(outbox))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals))
    monkeypatch.setenv("JARVIS_APPROVALS_TTL_SECONDS", "1200")
    monkeypatch.setenv("JARVIS_APPROVALS_DISPATCH_COOLDOWN_SECONDS", "30")
    monkeypatch.setenv("JARVIS_APPROVALS_DISPATCH_MAX_PER_RUN", "3")
    monkeypatch.setenv(
        "JARVIS_APPROVALS_DISPATCH_COOLDOWN_BY_KIND",
        "message_send:45, trade:120,invalid,nope:abc",
    )
    monkeypatch.setenv("JARVIS_CALENDAR_ICS", str(calendar))
    monkeypatch.setenv("JARVIS_MAIL_DRAFTS_PATH", str(drafts))
    monkeypatch.setenv("JARVIS_APPROVALS_API_HOST", "0.0.0.0")
    monkeypatch.setenv("JARVIS_APPROVALS_API_PORT", "9090")
    monkeypatch.setenv("JARVIS_APPROVAL_CHANNEL", "PUSHOVER")
    monkeypatch.setenv("JARVIS_TRADING_PAPER_BROKER", "FXOPEN")
    monkeypatch.setenv("JARVIS_MAC_PC_PIPELINE_MODE", "live")
    monkeypatch.setenv("JARVIS_MAC_PC_PIPELINE_SOURCE_ID", "mac-studio")
    monkeypatch.setenv("JARVIS_MAC_PC_PIPELINE_TARGET_ID", "pc-gaming")
    monkeypatch.setenv("JARVIS_MAC_PC_PIPELINE_TARGET_URL", "https://pc.example.local/bridge")
    monkeypatch.setenv("JARVIS_MAC_PC_PIPELINE_SHARED_SECRET", "bridge-secret")
    monkeypatch.setenv("JARVIS_VISION_HOST", "127.0.0.1")
    monkeypatch.setenv("JARVIS_VISION_PORT", "9031")
    monkeypatch.setenv("JARVIS_VISION_SOURCE", "iphone")
    monkeypatch.setenv("JARVIS_VISION_SECRET", "secret")
    monkeypatch.setenv("JARVIS_VISION_MAX_FRAME_BYTES", "4096")
    monkeypatch.setenv("JARVIS_VOICE_WAKE_WORD", "Friday")
    monkeypatch.setenv("JARVIS_VOICE_STT_PROVIDER", "whisperx")
    monkeypatch.setenv("JARVIS_VOICE_TTS_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "eleven-secret")
    monkeypatch.setenv("JARVIS_VOICE_TTS_MODEL", "eleven_flash_v2_5")
    monkeypatch.setenv("JARVIS_VOICE_TTS_DEFAULT_VOICE", "female")
    monkeypatch.setenv("JARVIS_VOICE_TTS_VOICE_ID_MALE", "voice-m")
    monkeypatch.setenv("JARVIS_VOICE_TTS_VOICE_ID_FEMALE", "voice-f")
    monkeypatch.setenv("JARVIS_VOICE_TTS_FALLBACK_PROVIDER", "coqui")
    monkeypatch.setenv("JARVIS_LOCATION_TOOLS_MODE", "live")
    monkeypatch.setenv("JARVIS_GOLD_MARKET_MODE", "live")
    monkeypatch.setenv("JARVIS_NEWS_SENTIMENT_MODE", "live")
    monkeypatch.setenv("JARVIS_HOME_ASSISTANT_URL", "http://ha.local:8123")
    monkeypatch.setenv("JARVIS_HOME_ASSISTANT_TOKEN", "ha-token")
    monkeypatch.setenv("JARVIS_HOME_ASSISTANT_TIMEOUT_SECONDS", "25")
    monkeypatch.setenv("JARVIS_TELEPHONY_PROVIDER", "twilio")
    monkeypatch.setenv("JARVIS_TELEPHONY_CALLER_ID", "+14155550000")
    monkeypatch.setenv("JARVIS_TELEPHONY_VAPI_ASSISTANT_ID", "assistant-123")
    monkeypatch.setenv("JARVIS_TELEPHONY_VAPI_PHONE_NUMBER_ID", "phone-123")
    monkeypatch.setenv("JARVIS_PAYMENTS_MONTHLY_CAP", "1500")
    monkeypatch.setenv("JARVIS_PAYMENTS_TX_LIMIT", "250")
    monkeypatch.setenv("JARVIS_PAYMENTS_ALLOWED_MCCS", "5812, 5411,5732")
    monkeypatch.setenv("JARVIS_PAYMENTS_BUDGET_DB", str(tmp_path / "payments-budget.db"))
    monkeypatch.setenv("JARVIS_PAYMENTS_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("JARVIS_TRADING_ACCOUNT_EQUITY", "250000")
    monkeypatch.setenv("JARVIS_TRADING_MAX_POSITION_PCT", "1.5")
    monkeypatch.setenv("JARVIS_TRADING_LIVE_COOLDOWN_SECONDS", "900")
    monkeypatch.setenv("JARVIS_TRADING_DAILY_DRAWDOWN_KILL_PCT", "4.5")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_TRADING_DAYS", "30")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_TRADES", "150")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_WIN_RATE", "0.55")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR", "1.25")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_AVG_R_MULTIPLE", "0.15")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MAX_ANOMALIES", "2")
    monkeypatch.setenv("JARVIS_CHAT_ACCOUNT_ID", "nick")
    monkeypatch.setenv("JARVIS_CHAT_AUTH_TOKEN", "chat-secret")
    monkeypatch.setenv("JARVIS_CHAT_ACCOUNTS", "nick:chat-secret,spouse:spouse-token")

    config = Config.from_env()

    assert config.message_send_mode == "dry_run"
    assert config.messaging_primary_channel == "slack"
    assert config.messaging_fallback_channels == ("sms", "push", "email")
    assert config.message_outbox == outbox
    assert config.approval_db == approvals
    assert config.approvals_ttl_seconds == 1200
    assert config.approvals_dispatch_cooldown_seconds == 30
    assert config.approvals_dispatch_max_per_run == 3
    assert config.approvals_dispatch_cooldown_by_kind == {
        "message_send": 45,
        "trade": 120,
    }
    assert config.calendar_ics == calendar
    assert config.mail_drafts_path == drafts
    assert config.approvals_api_host == "0.0.0.0"
    assert config.approvals_api_port == 9090
    assert config.mac_pc_pipeline_mode == "live"
    assert config.mac_pc_pipeline_source_id == "mac-studio"
    assert config.mac_pc_pipeline_target_id == "pc-gaming"
    assert config.mac_pc_pipeline_target_url == "https://pc.example.local/bridge"
    assert config.mac_pc_pipeline_shared_secret == "bridge-secret"
    assert config.approval_channel == "pushover"
    assert config.trading_paper_broker == "fxopen"
    assert config.vision_host == "127.0.0.1"
    assert config.vision_port == 9031
    assert config.vision_source_name == "iphone"
    assert config.vision_secret == "secret"
    assert config.vision_max_frame_bytes == 4096
    assert config.voice_wake_word == "friday"
    assert config.voice_stt_provider == "whisperx"
    assert config.voice_tts_provider == "elevenlabs"
    assert config.voice_tts_api_key == "eleven-secret"
    assert config.voice_tts_model == "eleven_flash_v2_5"
    assert config.voice_tts_default_voice == "female"
    assert config.voice_tts_voice_id_male == "voice-m"
    assert config.voice_tts_voice_id_female == "voice-f"
    assert config.voice_tts_fallback_provider == "coqui"
    assert config.location_tools_mode == "live"
    assert config.gold_market_mode == "live"
    assert config.news_sentiment_mode == "live"
    assert config.home_assistant_url == "http://ha.local:8123"
    assert config.home_assistant_token == "ha-token"
    assert config.home_assistant_timeout_seconds == 25
    assert config.telephony_provider == "twilio"
    assert config.telephony_caller_id == "+14155550000"
    assert config.telephony_vapi_assistant_id == "assistant-123"
    assert config.telephony_vapi_phone_number_id == "phone-123"
    assert config.payments_monthly_cap == 1500.0
    assert config.payments_tx_limit == 250.0
    assert config.payments_allowed_mccs == ("5812", "5411", "5732")
    assert config.payments_budget_db == tmp_path / "payments-budget.db"
    assert config.payments_webhook_secret == "whsec_test"
    assert config.trading_account_equity == 250000.0
    assert config.trading_max_position_pct == 1.5
    assert config.trading_live_cooldown_seconds == 900
    assert config.trading_daily_drawdown_kill_pct == 4.5
    assert config.trading_review_min_trading_days == 30
    assert config.trading_review_min_trades == 150
    assert config.trading_review_min_win_rate == 0.55
    assert config.trading_review_min_profit_factor == 1.25
    assert config.trading_review_min_avg_r_multiple == 0.15
    assert config.trading_review_max_anomalies == 2
    assert config.chat_account_id == "nick"
    assert config.chat_auth_token == "chat-secret"
    assert config.chat_accounts == {
        "nick": "chat-secret",
        "spouse": "spouse-token",
    }


def test_validate_rejects_smart_home_phase_without_home_assistant_config(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_smart_home=True,
        home_assistant_url="",
        home_assistant_token="",
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        msg = str(e)
        assert "JARVIS_PHASE_SMART_HOME requires JARVIS_HOME_ASSISTANT_URL" in msg
        assert "JARVIS_PHASE_SMART_HOME requires JARVIS_HOME_ASSISTANT_TOKEN" in msg


def test_validate_rejects_voice_phase_with_empty_wake_word(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_voice=True,
        voice_wake_word="",
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JARVIS_PHASE_VOICE requires JARVIS_VOICE_WAKE_WORD" in str(e)


def test_validate_rejects_elevenlabs_voice_phase_without_voice_ids(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_voice=True,
        voice_wake_word="jarvis",
        voice_stt_provider="faster-whisper",
        voice_tts_provider="elevenlabs",
        voice_tts_api_key="eleven-secret",
        voice_tts_voice_id_male="",
        voice_tts_voice_id_female="",
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        msg = str(e)
        assert "JARVIS_VOICE_TTS_PROVIDER=elevenlabs requires JARVIS_VOICE_TTS_VOICE_ID_MALE" in msg
        assert "JARVIS_VOICE_TTS_PROVIDER=elevenlabs requires JARVIS_VOICE_TTS_VOICE_ID_FEMALE" in msg


def test_validate_rejects_telephony_phase_without_caller_id_even_with_approvals(
    tmp_path,
):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=True,
        phase_telephony=True,
        telephony_caller_id="",
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JARVIS_PHASE_TELEPHONY requires JARVIS_TELEPHONY_CALLER_ID" in str(e)


def test_validate_allows_voice_smart_home_telephony_when_configured(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=True,
        phase_voice=True,
        phase_smart_home=True,
        phase_telephony=True,
        voice_wake_word="jarvis",
        voice_stt_provider="faster-whisper",
        voice_tts_provider="piper",
        home_assistant_url="http://ha.local:8123",
        home_assistant_token="token",
        telephony_caller_id="+14155550000",
    )

    config.validate()


def test_validate_rejects_payments_phase_without_approvals(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=False,
        phase_payments=True,
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JARVIS_PHASE_PAYMENTS requires JARVIS_PHASE_APPROVALS=true" in str(e)


def test_validate_rejects_telephony_phase_without_approvals(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=False,
        phase_telephony=True,
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JARVIS_PHASE_TELEPHONY requires JARVIS_PHASE_APPROVALS=true" in str(e)


def test_validate_rejects_trading_phase_without_approvals(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=False,
        phase_trading=True,
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JARVIS_PHASE_TRADING requires JARVIS_PHASE_APPROVALS=true" in str(e)


def test_validate_allows_gated_phases_when_approvals_enabled(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=True,
        phase_payments=True,
        phase_telephony=True,
        phase_trading=True,
        telephony_caller_id="+14155550000",
    )

    config.validate()


def test_validate_rejects_invalid_telephony_provider(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=True,
        phase_telephony=True,
        telephony_caller_id="+14155550000",
        telephony_provider="invalid",
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JARVIS_TELEPHONY_PROVIDER must be one of" in str(e)


def test_validate_rejects_vapi_telephony_without_required_settings(tmp_path):
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=True,
        phase_telephony=True,
        telephony_provider="vapi",
        telephony_caller_id="+14155550000",
        telephony_vapi_assistant_id="",
        telephony_vapi_phone_number_id="",
    )

    try:
        config.validate()
        assert False, "expected ValueError"
    except ValueError as e:
        msg = str(e)
        assert "VAPI_API_KEY" in msg
        assert "JARVIS_TELEPHONY_VAPI_ASSISTANT_ID" in msg
        assert "JARVIS_TELEPHONY_VAPI_PHONE_NUMBER_ID" in msg


def test_phase_enabled_returns_true_for_each_active_phase(tmp_path: Path) -> None:
    base: dict = dict(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
    )
    phase_fields = {
        "voice": "phase_voice",
        "smart_home": "phase_smart_home",
        "approvals": "phase_approvals",
        "payments": "phase_payments",
        "telephony": "phase_telephony",
        "trading": "phase_trading",
    }
    for phase_name, field_name in phase_fields.items():
        config = Config(**{**base, field_name: True})  # type: ignore[arg-type]
        assert config.phase_enabled(phase_name) is True, f"expected {phase_name} enabled"
        for other in phase_fields:
            if other != phase_name:
                assert config.phase_enabled(other) is False, f"expected {other} disabled"


def test_phase_enabled_returns_false_for_unknown_phase(tmp_path: Path) -> None:
    config = Config(
        anthropic_api_key="test",
        model="claude-sonnet-4-6",
        deployment_target="laptop",
        voice_stack="local",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        phase_approvals=True,
    )
    assert config.phase_enabled("not_a_phase") is False


def test_from_env_uses_selected_secret_provider(monkeypatch):
    monkeypatch.setenv("JARVIS_SECRET_PROVIDER", "env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak-test")
    monkeypatch.setenv("HELIUS_API_KEY", "hk-test")
    monkeypatch.setenv("JARVIS_HOME_ASSISTANT_TOKEN", "ha-secret")
    monkeypatch.setenv("JARVIS_WEBHOOK_SECRET", "wh-secret")
    monkeypatch.setenv("JARVIS_VISION_SECRET", "vision-secret")

    config = Config.from_env()

    assert config.secret_provider == "env"
    assert config.anthropic_api_key == "ak-test"
    assert config.helius_api_key == "hk-test"
    assert config.home_assistant_token == "ha-secret"
    assert config.webhook_secret == "wh-secret"
    assert config.vision_secret == "vision-secret"


def test_get_secret_fetches_value_at_call_time(monkeypatch):
    monkeypatch.setenv("JARVIS_SECRET_PROVIDER", "env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "first")
    config = Config.from_env()

    assert config.get_secret("ANTHROPIC_API_KEY") == "first"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "second")
    assert config.get_secret("ANTHROPIC_API_KEY") == "second"
