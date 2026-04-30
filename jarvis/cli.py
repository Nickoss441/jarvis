"""Chat REPL. Phase 1 entry point — `python3 -m jarvis`."""
import sys
from pathlib import Path

# Windows consoles default to cp1252 which can't handle emoji in AI responses
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .config import Config
from .audit import AuditLog
from .approval_service import ApprovalService
from .event_bus import EventBus
from .policy import Policy
from .brain import Brain
from .tools import ToolRegistry
from .voice_output import build_default_speaker, wants_vocal_reply
from .tools.web_search import web_search
from .tools.web_fetch import web_fetch
from .tools.notes import make_notes_tools
from .tools.recall import make_recall_tool
from .tools.events_recent import make_events_recent_tool
from .tools.location_current import make_location_current_tool
from .tools.message_send import make_message_send_tool
from .tools.call_phone import make_call_phone_tool
from .tools.reservation_call import make_reservation_call_tool
from .tools.payments import make_payments_tool
from .tools.trade import make_trade_tool
from .tools.calendar_read import make_calendar_read_tool
from .tools.mail_draft import make_mail_draft_tool
from .tools.user_preferences import make_user_preferences_tool
from .tools.home_assistant import make_home_assistant_tool
from .tools.sandbox import make_shell_run_tool, make_file_write_tool
from .tools.desktop_control import make_desktop_control_tool
from .tools.vision_observe import make_vision_observe_tool
from .tools.install_app import make_install_app_tool
from .tools.app_status import make_app_status_tool
from .tools.app_list import make_app_list_tool
from .tools.uninstall_app import make_uninstall_app_tool
from .tools.solana_helius import make_solana_helius_tools
from .tools.weather_now import make_weather_now_tool
from .tools.weather_here import make_weather_here_tool
from .tools.route_eta import make_route_eta_tool
from .tools.eta_to import make_eta_to_tool
from .tools.spotify import make_spotify_tool


SYSTEM_CONTROL_PROMPT = """You are Jarvis System Control, a local system-control agent for {user_name}.

Today is {date}.

You only have tools for local desktop and allowlisted app control:
    - desktop_control — inspect the active window, open or focus apps, open URLs, send keystrokes, type text, and take screenshots
    - app_status — check whether an allowlisted macOS app is installed
    - app_list — list allowlisted macOS apps and installation status
    - install_app — request install of an allowlisted app
    - uninstall_app — request uninstall of an allowlisted app

Operating style:
- Be concise and execution-focused.
- Prefer checking app or window state before acting when that can prevent mistakes.
- Do not claim desktop changes succeeded unless a tool result confirms it.
- If a request needs unavailable tools, say so briefly rather than improvising.
- Ask one focused clarifying question if the target app or action is ambiguous.
"""


def build_brain_from_config(config: Config, system_prompt_template: str | None = None) -> Brain:
    audit = AuditLog(config.audit_db)
    policy_path = Path(__file__).parent.parent / "policies.yaml"
    policy = Policy.from_file(
        policy_path,
        enabled_phases=config.enabled_phases(),
    )
    approval_service = ApprovalService(config)

    tools = ToolRegistry()
    tools.register(web_search)
    tools.register(web_fetch)
    for t in make_notes_tools(config.notes_dir):
        tools.register(t)
    tools.register(make_recall_tool(audit))
    tools.register(make_events_recent_tool(EventBus(config.event_bus_db)))
    tools.register(make_location_current_tool(EventBus(config.event_bus_db)))
    tools.register(make_calendar_read_tool(config.calendar_ics))
    tools.register(make_mail_draft_tool(config.mail_drafts_path))
    preferences_path = config.user_preferences_store_path or (config.audit_db.parent / "preferences.json")
    tools.register(
        make_user_preferences_tool(
            preferences_path,
            manifest_secret=(config.get_secret("JARVIS_USER_MANIFEST_SECRET") or ""),
        )
    )
    tools.register(make_spotify_tool())
    tools.register(make_weather_now_tool(mode=config.location_tools_mode))
    tools.register(make_route_eta_tool(mode=config.location_tools_mode))
    tools.register(make_weather_here_tool(EventBus(config.event_bus_db), mode=config.location_tools_mode))
    tools.register(make_eta_to_tool(EventBus(config.event_bus_db), mode=config.location_tools_mode))
    if config.phase_smart_home:
        tools.register(
            make_home_assistant_tool(
                ha_url=config.home_assistant_url,
                ha_token_getter=lambda: (
                    config.get_secret("HOME_ASSISTANT_TOKEN")
                    or config.home_assistant_token
                ),
                mode=("live" if config.home_assistant_url else "dry_run"),
                timeout_seconds=config.home_assistant_timeout_seconds,
            )
        )
    for t in make_solana_helius_tools(
        api_key=config.helius_api_key,
        network=config.helius_network,
        api_key_getter=lambda: config.get_secret("HELIUS_API_KEY") or config.helius_api_key,
    ):
        tools.register(t)
    if config.phase_sandbox:
        tools.register(
            make_shell_run_tool(
                sandbox_dir=config.sandbox_dir,
                mode="live",
                timeout_seconds=config.sandbox_shell_timeout_seconds,
            )
        )
        tools.register(
            make_file_write_tool(
                sandbox_dir=config.sandbox_dir,
                mode="live",
            )
        )
        tools.register(
            make_desktop_control_tool(mode="live")
        )
        tools.register(
            make_vision_observe_tool(mode="live")
        )
        tools.register(
            make_install_app_tool(
                mode="live",
                request_approval=approval_service.request,
                get_approval=approval_service.store.get,
            )
        )
        tools.register(
            make_app_status_tool(mode="live")
        )
        tools.register(
            make_app_list_tool(mode="live")
        )
        tools.register(
            make_uninstall_app_tool(
                mode="live",
                request_approval=approval_service.request,
                get_approval=approval_service.store.get,
            )
        )
    tools.register(
        make_message_send_tool(
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
        )
    )
    tools.register(
        make_call_phone_tool(
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
        )
    )
    tools.register(
        make_reservation_call_tool(
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
            user_name=config.user_name,
        )
    )
    tools.register(
        make_payments_tool(
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
        )
    )
    tools.register(
        make_trade_tool(
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
            account_equity=config.trading_account_equity,
            max_position_pct=config.trading_max_position_pct,
        )
    )

    return Brain(config, audit, policy, tools, system_prompt_template=system_prompt_template)


def build_system_control_brain_from_config(config: Config) -> Brain:
    if not config.phase_sandbox:
        raise ValueError("system-control requires JARVIS_PHASE_SANDBOX=true")

    audit = AuditLog(config.audit_db)
    policy_path = Path(__file__).parent.parent / "policies.yaml"
    policy = Policy.from_file(
        policy_path,
        enabled_phases=config.enabled_phases(),
    )
    approval_service = ApprovalService(config)

    tools = ToolRegistry()
    tools.register(make_desktop_control_tool(mode="live"))
    tools.register(make_app_status_tool(mode="live"))
    tools.register(make_app_list_tool(mode="live"))
    tools.register(
        make_install_app_tool(
            mode="live",
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
        )
    )
    tools.register(
        make_uninstall_app_tool(
            mode="live",
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
        )
    )

    return Brain(
        config,
        audit,
        policy,
        tools,
        system_prompt_template=SYSTEM_CONTROL_PROMPT,
    )


def build_brain() -> Brain:
    config = Config.from_env()
    config.validate()
    return build_brain_from_config(config)


def build_system_control_brain() -> Brain:
    config = Config.from_env()
    config.validate()
    return build_system_control_brain_from_config(config)


def repl() -> None:
    print("Jarvis (phase 1) — type 'quit' to exit, 'reset' to clear conversation.\n")

    try:
        brain = build_brain()
    except Exception as e:
        print(f"Startup error: {e}")
        sys.exit(1)

    speaker = build_default_speaker()

    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user:
            continue
        if user.lower() in ("quit", "exit"):
            break
        if user.lower() == "reset":
            brain.conversation.reset()
            print("(conversation cleared)\n")
            continue

        try:
            reply = brain.turn(user)
            print(f"jarvis > {reply}\n")
            if wants_vocal_reply(user):
                speaker.speak(reply)
        except KeyboardInterrupt:
            print("\n(interrupted)\n")
        except Exception as e:
            print(f"(error: {e.__class__.__name__}: {e})\n")


def repl_system_control() -> None:
    print("Jarvis System Control — type 'quit' to exit, 'reset' to clear conversation.\n")

    try:
        brain = build_system_control_brain()
    except Exception as e:
        print(f"Startup error: {e}")
        sys.exit(1)

    speaker = build_default_speaker()

    while True:
        try:
            user = input("system > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user:
            continue
        if user.lower() in ("quit", "exit"):
            break
        if user.lower() == "reset":
            brain.conversation.reset()
            print("(conversation cleared)\n")
            continue

        try:
            reply = brain.turn(user)
            print(f"jarvis > {reply}\n")
            if wants_vocal_reply(user):
                speaker.speak(reply)
        except KeyboardInterrupt:
            print("\n(interrupted)\n")
        except Exception as e:
            print(f"(error: {e.__class__.__name__}: {e})\n")


if __name__ == "__main__":
    repl()
