"""Minimal HTTP API surface for approval operations."""
from dataclasses import asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .approval import ApprovalEnvelope
from .approval_service import ApprovalService
from .cli import build_brain_from_config
from .config import Config
from .event_bus import EventBus
from .monitor_runner import MonitorRunner, register_configured_monitors
from .payments_ledger import PaymentsBudgetLedger
from .perception.chat import build_chat_registry, parse_sms_command
from .runtime import RuntimeEventEnvelope
from .trade_review import (
    generate_trade_review_artifact,
    list_recent_trade_review_artifacts,
    load_trade_review_artifact,
    load_latest_trade_review_artifact,
)


REACT_HUD_ASSETS = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "data/april_27_dialogue.json": "application/json; charset=utf-8",
}
REACT_HUD_DIR = Path(__file__).resolve().parent / "web" / "hud_react"

COMMAND_CENTER_ASSETS = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
}
COMMAND_CENTER_DIR = Path(__file__).resolve().parent / "web" / "command_center"

JARVIS_HOME_ASSETS = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
}
JARVIS_HOME_DIR = Path(__file__).resolve().parent / "web" / "jarvis_home"

NEWS_SOURCES = {
    "reuters": [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://feeds.reuters.com/reuters/businessNews",
    ],
}


def _parse_rss_datetime(raw: str) -> int:
    text = str(raw or "").strip()
    if not text:
        return 0
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _fetch_news_items(feed_url: str, source: str, per_feed_limit: int = 10) -> list[dict[str, object]]:
    req = Request(feed_url, headers={"User-Agent": "JarvisHUD/1.0"})
    try:
        with urlopen(req, timeout=6) as resp:  # noqa: S310 - fixed HTTPS feeds only
            raw = resp.read()
    except (URLError, TimeoutError, OSError):
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    entries: list[dict[str, object]] = []
    for item in root.findall("./channel/item")[:per_feed_limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        entries.append(
            {
                "title": title,
                "url": link,
                "published": pub_raw,
                "published_unix": _parse_rss_datetime(pub_raw),
                "source": source,
            }
        )
    return entries


def _latest_news_payload(source: str, limit: int) -> dict[str, object]:
    key = source.strip().lower() if source else "reuters"
    feeds = NEWS_SOURCES.get(key)
    if not feeds:
        return {"source": key, "items": [], "error": "unknown source"}

    merged: list[dict[str, object]] = []
    for url in feeds:
        merged.extend(_fetch_news_items(url, key))

    deduped: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for row in sorted(merged, key=lambda x: int(x.get("published_unix") or 0), reverse=True):
        news_url = str(row.get("url") or "")
        if not news_url or news_url in seen_urls:
            continue
        seen_urls.add(news_url)
        deduped.append(row)
        if len(deduped) >= max(1, min(limit, 20)):
            break

    return {
        "source": key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": deduped,
    }


UI_HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Jarvis Approvals</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
    <style>
        :root {
            --bg:     #060a14;
            --card:   rgba(0,220,255,0.038);
            --border: rgba(0,220,255,0.13);
            --text:   #f0f8ff;
            --text2:  rgba(180,225,255,0.48);
            --text3:  rgba(180,225,255,0.22);
            --cyan:   #00e5ff;
            --green:  #30d158;
            --red:    #ff453a;
            --orange: #ff9f0a;
            --font:   "Inter", -apple-system, "Segoe UI", sans-serif;
            --mono:   "JetBrains Mono", "SF Mono", monospace;
            --r:      12px;
            /* legacy aliases so old JS still works */
            --bg-0: #060a14;
            --bg-1: #060a14;
            --glass: rgba(0,220,255,0.038);
            --glass-strong: rgba(0,220,255,0.06);
            --line: rgba(0,220,255,0.13);
            --line-bright: rgba(0,229,255,0.4);
            --muted: rgba(180,225,255,0.48);
            --accent: #00e5ff;
            --alert: #ff453a;
            --ok: #30d158;
            --gold: #ff9f0a;
        }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font);
            font-size: 14px;
            color: var(--text);
            background: var(--bg);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }
        body::before {
            content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
            background-image:
                radial-gradient(ellipse 70% 55% at 50% 50%, rgba(0,90,200,0.1) 0%, transparent 65%),
                linear-gradient(rgba(0,220,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,220,255,0.02) 1px, transparent 1px);
            background-size: 100% 100%, 52px 52px, 52px 52px;
        }
        .ambient-grid, .connector-layer, .globe-wrap, .spark { display: none; }
        .wrap {
            position: relative; z-index: 1;
            max-width: 1260px; margin: 0 auto;
            padding: 16px 18px 40px;
        }
        .page-header {
            display: flex; align-items: center; gap: 12px;
            padding: 14px 0 16px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
        }
        .nav-chips { display: flex; gap: 6px; margin-left: auto; }
        .nav-chip {
            font-family: var(--mono); font-size: 10px; color: var(--text2);
            border: 1px solid var(--border); border-radius: 20px;
            padding: 2px 10px; text-decoration: none; letter-spacing: 0.04em;
            transition: border-color 0.15s, color 0.15s;
        }
        .nav-chip:hover { border-color: var(--cyan); color: var(--cyan); }
        .page-header h1 {
            font-size: 13px; font-weight: 600; font-family: var(--mono);
            letter-spacing: 0.08em; text-transform: uppercase;
            color: var(--cyan); text-shadow: 0 0 12px rgba(0,229,255,0.3);
        }
        .page-header .dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: var(--green); box-shadow: 0 0 6px var(--green);
            animation: live-pulse 2.2s ease-in-out infinite; flex-shrink: 0;
        }
        .hud {
            display: grid;
            grid-template-columns: 220px 1fr 250px;
            gap: 12px; align-items: start;
        }
        .stack { display: grid; gap: 12px; }
        .panel {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px; padding: 14px 16px;
            backdrop-filter: blur(18px);
            position: relative;
        }
        .panel::before {
            content: ""; position: absolute; top: 0; left: 50%;
            transform: translateX(-50%); width: 60%; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07), transparent);
            pointer-events: none;
        }
        .panel h3 {
            font-family: var(--mono); font-size: 9px; font-weight: 500;
            text-transform: uppercase; letter-spacing: 0.15em;
            color: var(--text2); margin-bottom: 10px;
        }
        .panel .sub { display: none; }
        .center-hub { border-top: 1px solid rgba(255,159,10,0.4); }
        .stack > .panel:first-child { border-top: 1px solid rgba(0,229,255,0.4); }
        .stack > .panel:nth-child(2) { border-top: 1px solid rgba(48,209,88,0.4); }
        .stack > .panel:nth-child(3) { border-top: 1px solid rgba(191,90,242,0.4); }
        .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .metric {
            background: rgba(0,220,255,0.03);
            border: 1px solid var(--border);
            border-radius: 8px; padding: 10px 12px;
        }
        .metric .label {
            font-family: var(--mono); font-size: 9px;
            text-transform: uppercase; letter-spacing: 0.12em; color: var(--text2);
        }
        .metric .value {
            margin-top: 5px; font-size: 22px; font-weight: 300;
            letter-spacing: -0.02em; color: var(--cyan);
            text-shadow: 0 0 14px rgba(0,229,255,0.3);
        }
        .summary-bar, #status, #chatStatus, #appStatusDiv {
            margin-top: 8px; padding: 9px 12px;
            background: rgba(0,0,0,0.22);
            border: 1px solid rgba(0,220,255,0.1);
            border-radius: 8px;
            font-family: var(--mono); font-size: 11px; line-height: 1.6;
            color: rgba(180,225,255,0.65);
            white-space: pre-wrap; min-height: 32px;
        }
        .title {
            font-size: 17px; font-weight: 600; letter-spacing: -0.02em;
            margin-bottom: 3px; color: var(--text);
        }
        .muted {
            font-family: var(--mono); font-size: 10px; color: var(--text2);
            letter-spacing: 0.04em; margin-bottom: 12px; display: block;
        }
        .toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
        button {
            font-family: var(--mono); font-size: 10px; font-weight: 500;
            letter-spacing: 0.08em; text-transform: uppercase;
            color: var(--text);
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 7px; padding: 7px 14px;
            cursor: pointer;
            transition: background 0.15s, border-color 0.15s;
            user-select: none;
        }
        button:hover  { background: rgba(255,255,255,0.09); border-color: rgba(255,255,255,0.2); }
        button:active { background: rgba(255,255,255,0.03); }
        button:disabled { opacity: 0.35; cursor: not-allowed; }
        button.primary {
            background: rgba(0,229,255,0.1); color: var(--cyan);
            border-color: rgba(0,229,255,0.28);
        }
        button.primary:hover { background: rgba(0,229,255,0.18); }
        button.ok {
            background: rgba(48,209,88,0.1); color: var(--green);
            border-color: rgba(48,209,88,0.28);
        }
        button.ok:hover { background: rgba(48,209,88,0.18); }
        button.danger {
            background: rgba(255,69,58,0.08); color: var(--red);
            border-color: rgba(255,69,58,0.28);
        }
        button.danger:hover { background: rgba(255,69,58,0.18); }
        button.ghost { background: transparent; border-color: var(--border); }
        button.ghost:hover { background: rgba(255,255,255,0.05); }
        select, input, textarea {
            width: 100%; font-family: var(--mono); font-size: 11px;
            color: var(--text); background: rgba(0,220,255,0.04);
            border: 1px solid rgba(0,220,255,0.16);
            border-radius: 7px; padding: 7px 10px; outline: none;
            transition: border-color 0.2s;
        }
        select:focus, input:focus, textarea:focus {
            border-color: rgba(0,220,255,0.4);
            box-shadow: 0 0 10px rgba(0,220,255,0.07);
        }
        textarea { resize: vertical; min-height: 80px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 12px; }
        th {
            font-family: var(--mono); font-size: 9px; font-weight: 500;
            text-transform: uppercase; letter-spacing: 0.12em;
            color: var(--text2); padding: 8px 10px;
            border-bottom: 1px solid var(--border); text-align: left;
        }
        td {
            padding: 9px 10px; border-bottom: 1px solid rgba(0,220,255,0.06);
            vertical-align: top; color: var(--text);
        }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(0,220,255,0.03); }
        td code {
            font-family: var(--mono); font-size: 10px;
            background: rgba(0,220,255,0.07); color: var(--cyan);
            padding: 2px 6px; border-radius: 4px;
        }
        .row  { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
        .field { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 160px; }
        .field label {
            font-family: var(--mono); font-size: 9px; font-weight: 500;
            letter-spacing: 0.1em; text-transform: uppercase; color: var(--text2);
        }
        .field input, .field textarea {
            border: 1px solid rgba(0,220,255,0.2);
            background: rgba(0,220,255,0.04);
        }
        .field textarea { min-height: 80px; resize: vertical; }
        .chat { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); }
        .chat h2 { font-size: 15px; font-weight: 600; margin-bottom: 10px; }
        #chatTranscript {
            margin-top: 10px; padding: 10px;
            border: 1px solid var(--border); border-radius: 10px;
            background: rgba(0,0,0,0.18); max-height: 220px; overflow-y: auto;
        }
        .chat-line {
            margin: 0 0 6px; padding: 7px 10px; border-radius: 7px;
            white-space: pre-wrap; line-height: 1.4; font-size: 11px; font-family: var(--mono);
        }
        .chat-user  { background: rgba(0,229,255,0.07); border: 1px solid rgba(0,229,255,0.18); }
        .chat-agent { background: rgba(48,209,88,0.07); border: 1px solid rgba(48,209,88,0.18); }
        .chat-error { background: rgba(255,69,58,0.07); border: 1px solid rgba(255,69,58,0.18); }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes live-pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.35; transform: scale(0.65); }
        }
        @media (max-width: 1000px) { .hud { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="page-header">
            <div class="dot"></div>
            <h1>Jarvis — Approval Queue</h1>
            <div class="nav-chips">
                <a class="nav-chip" href="/hud/cc">Command Center</a>
                <a class="nav-chip" href="/hud/react">HUD React</a>
            </div>
        </div>
        <div class="hud">
            <div class="stack">
                <section class="panel">
                    <h3>Market Data</h3>
                    <p class="sub">Oil and Gold signal stream</p>
                    <div class="metrics">
                        <div class="metric">
                            <div class="label">Oil</div>
                            <div id="oilPrice" class="value">78.40</div>
                        </div>
                        <div class="metric">
                            <div class="label">Gold</div>
                            <div id="goldPrice" class="value">2320.2</div>
                        </div>
                    </div>
                    <svg class="spark" viewBox="0 0 220 64" preserveAspectRatio="none" aria-hidden="true">
                        <polyline id="sparkMarket" fill="none" stroke="#5bbcff" stroke-width="2" points="0,41 20,37 40,38 60,31 80,34 100,28 120,30 140,26 160,29 180,24 200,22 220,18" />
                    </svg>
                </section>

                <section class="panel">
                    <h3>Geospatial Alert</h3>
                    <p class="sub">Live radar focus</p>
                    <div class="summary-bar" id="geoAlert">Focus region: Strait of Hormuz. Threat level normal.</div>
                </section>

                <section class="panel">
                    <h3>Schedule</h3>
                    <p class="sub">Upcoming timeline</p>
                    <div class="summary-bar">7:00 PM - Ops review<br/>8:30 PM - Crypto check-in<br/>10:00 PM - Daily close</div>
                </section>
            </div>

            <section class="panel center-hub">
                <svg class="connector-layer" viewBox="0 0 1000 700" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M500 286 C390 216, 245 182, 96 122" fill="none" stroke="rgba(84,178,255,0.48)" stroke-width="1.5" />
                    <path d="M500 286 C390 320, 230 376, 86 464" fill="none" stroke="rgba(84,178,255,0.34)" stroke-width="1.3" />
                    <path d="M500 286 C620 222, 770 164, 930 128" fill="none" stroke="rgba(84,178,255,0.48)" stroke-width="1.5" />
                    <path d="M500 286 C620 330, 794 404, 938 518" fill="none" stroke="rgba(84,178,255,0.34)" stroke-width="1.3" />
                </svg>

                <h1 class="title">Jarvis Approval Queue</h1>
                <p class="muted">Review pending approvals and dispatch approved actions.</p>

                <div class="globe-wrap" aria-hidden="true">
                    <div class="orbit"></div>
                    <div class="globe"></div>
                    <div class="poi p1"></div>
                    <div class="poi p2"></div>
                    <div class="poi p3"></div>
                </div>

                <div class="summary-bar" id="liveSummary">Live transcript: awaiting latest command context...</div>

                <div class="toolbar">
                    <button class="primary" onclick="loadPending()">Refresh Pending</button>
                    <button class="ok" onclick="dispatchApproved()">Dispatch Approved</button>
                </div>

                <table id="pendingTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Kind</th>
                            <th>Payload</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
                <div id="status"></div>
            </section>

            <div class="stack">
                <section class="panel">
                    <h3>App Lifecycle</h3>
                    <p class="sub">Install, check, and remove apps</p>
                    <div class="row">
                        <div class="field" style="min-width: 100%;">
                            <label for="appSelector">App</label>
                            <select id="appSelector" name="app">
                                <option value="">Select an app...</option>
                                <option value="arc">Arc</option>
                                <option value="spotify">Spotify</option>
                                <option value="visual studio code">Visual Studio Code</option>
                                <option value="google chrome">Google Chrome</option>
                                <option value="slack">Slack</option>
                            </select>
                        </div>
                    </div>
                    <div class="toolbar">
                        <button class="primary" onclick="requestAppStatus()">Check Status</button>
                        <button class="ok" onclick="requestAppInstall()">Install</button>
                        <button class="danger" onclick="requestAppUninstall()">Uninstall</button>
                    </div>
                    <div id="appStatus" style="margin-top: 10px; padding: 10px; border-radius: 8px; border: 1px solid var(--line); background: rgba(9, 20, 38, 0.7); font-family: 'IBM Plex Mono', 'SFMono-Regular', monospace; font-size: 12px; min-height: 26px; white-space: pre-wrap; display: none;"></div>
                </section>

                <section class="panel">
                    <h3>Trade Review Policy</h3>
                    <p class="sub">Active live-unlock thresholds from config</p>
                    <div class="summary-bar" style="white-space: pre-wrap; line-height: 1.6;">
Min trading days: __TRADE_REVIEW_MIN_TRADING_DAYS__
Min paper trades: __TRADE_REVIEW_MIN_TRADES__
Min win rate: __TRADE_REVIEW_MIN_WIN_RATE__
Min profit factor: __TRADE_REVIEW_MIN_PROFIT_FACTOR__
Min avg R multiple: __TRADE_REVIEW_MIN_AVG_R_MULTIPLE__
Max anomalies: __TRADE_REVIEW_MAX_ANOMALIES__
Daily drawdown guardrail: __TRADE_REVIEW_DRAWDOWN_LIMIT__
                    </div>
                    <div class="row" style="margin-top: 10px;">
                        <div class="field">
                            <label for="tradeReviewReviewer">Reviewer</label>
                            <input id="tradeReviewReviewer" type="text" placeholder="Ops" />
                        </div>
                        <div class="field">
                            <label for="tradeReviewVersion">Strategy Version</label>
                            <input id="tradeReviewVersion" type="text" placeholder="v1.2.3" />
                        </div>
                    </div>
                    <div class="toolbar">
                        <button class="primary" onclick="generateTradeReviewArtifact()">Generate Review Artifact</button>
                        <button onclick="downloadTradeReviewArtifact()">Download Selected Review</button>
                    </div>
                    <div class="toolbar" style="margin-top: 8px;">
                        <button onclick="downloadTradeReviewSupportingArtifact('trade_performance_report')">Performance JSON</button>
                        <button onclick="downloadTradeReviewSupportingArtifact('trade_replay_report')">Replay JSON</button>
                        <button onclick="downloadTradeReviewSupportingArtifact('audit_export')">Audit JSONL</button>
                    </div>
                    <div id="tradeReviewStatus" style="margin-top: 10px; padding: 10px; border-radius: 8px; border: 1px solid var(--line); background: rgba(9, 20, 38, 0.7); font-family: 'IBM Plex Mono', 'SFMono-Regular', monospace; font-size: 12px; min-height: 26px; white-space: pre-wrap; display: none;"></div>
                    <div style="margin-top: 10px; font-size: 12px; color: rgba(208, 221, 255, 0.72); text-transform: uppercase; letter-spacing: 0.08em;">Latest Review Preview</div>
                    <div id="tradeReviewPreview" style="margin-top: 8px; padding: 12px; border-radius: 8px; border: 1px solid var(--line); background: rgba(6, 14, 28, 0.92); font-family: 'IBM Plex Mono', 'SFMono-Regular', monospace; font-size: 12px; min-height: 72px; max-height: 280px; overflow: auto; white-space: pre-wrap; display: none;"></div>
                    <div style="margin-top: 12px; font-size: 12px; color: rgba(208, 221, 255, 0.72); text-transform: uppercase; letter-spacing: 0.08em;">Recent Reviews</div>
                    <div id="tradeReviewHistory" style="margin-top: 8px; display: grid; gap: 8px;"></div>
                </section>

                <section class="panel">
                    <h3>Social Metrics</h3>
                    <p class="sub">Community pulse</p>
                    <div class="metrics">
                        <div class="metric">
                            <div class="label">Followers</div>
                            <div id="followersCount" class="value">+356</div>
                        </div>
                        <div class="metric">
                            <div class="label">Bitcoin</div>
                            <div id="btcPrice" class="value">$68.2k</div>
                        </div>
                    </div>
                    <svg class="spark" viewBox="0 0 220 64" preserveAspectRatio="none" aria-hidden="true">
                        <polyline id="sparkBitcoin" fill="none" stroke="#f2c66b" stroke-width="2" points="0,30 20,32 40,27 60,29 80,24 100,25 120,18 140,19 160,15 180,17 200,13 220,14" />
                    </svg>
                </section>

                <section class="panel chat">
                    <h2>Chat with Jarvis</h2>
                    <p class="sub">Send a direct message through <code>/chat/inbound</code> and load context via <code>/chat/history</code>.</p>
                    <div class="row">
                        <div class="field">
                            <label for="chatAccount">Account ID</label>
                            <input id="chatAccount" name="account_id" type="text" placeholder="nick" />
                        </div>
                        <div class="field">
                            <label for="chatToken">Token</label>
                            <input id="chatToken" name="token" type="password" placeholder="chat-secret" />
                        </div>
                    </div>
                    <div class="row">
                        <div class="field" style="min-width: 100%;">
                            <label for="chatText">Message</label>
                            <textarea id="chatText" name="text" placeholder="hey jarvis, help me plan tomorrow"></textarea>
                        </div>
                    </div>
                    <div class="toolbar">
                        <button onclick="loadChatHistory()">Load History</button>
                        <button class="primary" onclick="sendChat()">Send Message</button>
                    </div>
                    <p class="sub">Tip: press Ctrl+Enter (or Cmd+Enter on Mac) to send quickly.</p>
                    <div id="chatTranscript"></div>
                    <div id="chatStatus"></div>
                </section>
            </div>
        </div>
    </div>
    <script>
        let currentTradeReviewId = '';
        let currentTradeReviewArtifacts = {};

        async function apiGet(path) {
            const res = await fetch(path);
            return {status: res.status, body: await res.json()};
        }

        async function apiPost(path, payload) {
            const res = await fetch(path, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload || {})
            });
            return {status: res.status, body: await res.json()};
        }

        function setStatus(obj) {
            document.getElementById('status').textContent = JSON.stringify(obj, null, 2);
        }

        function rowFor(item) {
            const tr = document.createElement('tr');
            const payload = JSON.stringify(item.payload);
            tr.innerHTML = `
                <td><code>${item.id}</code></td>
                <td>${item.kind}</td>
                <td><code>${payload}</code></td>
                <td>
                    <button class="ok" data-id="${item.id}" data-action="approve">Approve</button>
                    <button class="danger" data-id="${item.id}" data-action="reject">Reject</button>
                </td>
            `;
            tr.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    const action = btn.getAttribute('data-action');
                    const reason = action + ' from web ui';
                    const out = await apiPost(`/approvals/${id}/${action}`, {reason});
                    setStatus(out);
                    await loadPending();
                });
            });
            return tr;
        }

        function updateLiveSummary(text) {
            const el = document.getElementById('liveSummary');
            if (el) {
                el.textContent = `Live transcript: ${text}`;
            }
        }

        async function loadPending() {
            const out = await apiGet('/approvals/pending?limit=100');
            const tbody = document.querySelector('#pendingTable tbody');
            tbody.innerHTML = '';
            for (const item of out.body.items || []) {
                tbody.appendChild(rowFor(item));
            }
            if (!out.body.items || out.body.items.length === 0) {
                const tr = document.createElement('tr');
                tr.innerHTML = '<td colspan="4">No pending approvals.</td>';
                tbody.appendChild(tr);
                updateLiveSummary('No active approvals. System stable.');
            } else {
                updateLiveSummary(`Priority update: ${out.body.items.length} approval item(s) await review.`);
            }
            setStatus(out);
        }

        async function dispatchApproved() {
            const out = await apiPost('/approvals/dispatch', {limit: 100});
            setStatus(out);
            updateLiveSummary('Dispatch cycle executed. Verifying queue integrity.');
            await loadPending();
        }

        function setChatStatus(obj) {
            document.getElementById('chatStatus').textContent = JSON.stringify(obj, null, 2);
        }

        function appendChatLine(role, text) {
            const box = document.getElementById('chatTranscript');
            const line = document.createElement('div');
            const roleLabel = role === 'user' ? 'You' : (role === 'agent' ? 'Jarvis' : 'Error');
            line.className = `chat-line ${role === 'user' ? 'chat-user' : (role === 'agent' ? 'chat-agent' : 'chat-error')}`;
            line.textContent = `${roleLabel}: ${text}`;
            box.appendChild(line);
            box.scrollTop = box.scrollHeight;
        }

        function getFieldValue(selectors, trim = true) {
            for (const selector of selectors) {
                const el = document.querySelector(selector);
                if (!el || typeof el.value !== 'string') {
                    continue;
                }
                return trim ? el.value.trim() : el.value;
            }
            return '';
        }

        async function loadChatHistory() {
            const accountId = getFieldValue(['#chatAccount', '#chat_account', 'input[name="account_id"]']);
            const token = getFieldValue(['#chatToken', '#chat_token', 'input[name="token"]']);
            const transcript = document.getElementById('chatTranscript');

            if (!accountId || !token) {
                setChatStatus({error: 'account_id and token are required to load history'});
                return;
            }

            const query = `account_id=${encodeURIComponent(accountId)}&token=${encodeURIComponent(token)}&limit=20`;
            const out = await apiGet(`/chat/history?${query}`);
            setChatStatus(out);
            transcript.innerHTML = '';

            const items = out && out.body && Array.isArray(out.body.items) ? out.body.items : [];
            for (const item of items) {
                if (item && typeof item.text === 'string') {
                    appendChatLine('user', item.text);
                }
            }
            updateLiveSummary(`Loaded ${items.length} historical message(s) from /chat/history.`);
        }

        async function sendChat() {
            const accountId = getFieldValue(['#chatAccount', '#chat_account', 'input[name="account_id"]']);
            const token = getFieldValue(['#chatToken', '#chat_token', 'input[name="token"]']);
            const text = getFieldValue(['#chatText', '#chat_text', 'textarea[name="text"]', 'textarea[name="message"]']);
            const sendButton = document.querySelector('button.primary[onclick="sendChat()"]');

            if (!accountId || !token || !text) {
                setChatStatus({error: 'account_id, token, and message are required'});
                appendChatLine('error', 'account_id, token, and message are required');
                return;
            }

            appendChatLine('user', text);
            if (sendButton) {
                sendButton.disabled = true;
            }

            const out = await apiPost('/chat/inbound', {
                account_id: accountId,
                token,
                source: 'web_ui',
                text,
            });
            setChatStatus(out);

            const reply = out && out.body && typeof out.body.reply === 'string' ? out.body.reply : '';
            const replyError = out && out.body && typeof out.body.reply_error === 'string' ? out.body.reply_error : '';

            if (reply) {
                appendChatLine('agent', reply);
                updateLiveSummary(`Jarvis response: ${reply.slice(0, 120)}${reply.length > 120 ? '...' : ''}`);
            } else if (replyError) {
                appendChatLine('error', replyError);
                updateLiveSummary(`Agent error: ${replyError}`);
            } else if (out.status >= 400) {
                appendChatLine('error', 'Request failed');
                updateLiveSummary('Request failed while sending message to /chat/inbound.');
            }

            document.getElementById('chatText').value = '';
            if (sendButton) {
                sendButton.disabled = false;
            }
        }

        function jitterValue(elId, step, decimals = 1, prefix = '', suffix = '') {
            const el = document.getElementById(elId);
            if (!el) {
                return;
            }
            const raw = String(el.textContent || '').replace(/[^0-9.-]/g, '');
            const base = Number(raw || 0);
            const next = Math.max(0, base + ((Math.random() - 0.5) * step));
            el.textContent = `${prefix}${next.toFixed(decimals)}${suffix}`;
        }

        function tickDashboard() {
            jitterValue('oilPrice', 0.8, 2);
            jitterValue('goldPrice', 3.2, 1);
            jitterValue('btcPrice', 0.7, 1, '$', 'k');
            jitterValue('followersCount', 5, 0, '+');
            const states = [
                'Focus region: Strait of Hormuz. Threat level normal.',
                'Focus region: Eastern Med. Shipping density elevated.',
                'Focus region: North Atlantic. Weather route advisory active.',
            ];
            const alert = document.getElementById('geoAlert');
            if (alert) {
                const index = Math.floor(Math.random() * states.length);
                alert.textContent = states[index];
            }
        }

        document.getElementById('chatText').addEventListener('keydown', (event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                event.preventDefault();
                sendChat();
            }
        });

        async function requestAppStatus() {
            const appSelector = document.getElementById('appSelector');
            const app = appSelector ? appSelector.value : '';
            if (!app) {
                setAppStatusDiv('Please select an app first.');
                return;
            }

            setAppStatusDiv(`Checking status of ${app}...`);
            const out = await apiPost('/approvals/request', {
                kind: 'app_status',
                payload: { app },
            });

            if (out.status >= 400) {
                setAppStatusDiv(`Error: ${out.error || 'Failed to request status'}`);
            } else {
                const approval = out.body && out.body.approval ? out.body.approval : {};
                setAppStatusDiv(`Status request queued.\nApproval ID: ${approval.id || 'unknown'}\nKind: app_status`);
                loadPending();
            }
        }

        async function requestAppInstall() {
            const appSelector = document.getElementById('appSelector');
            const app = appSelector ? appSelector.value : '';
            if (!app) {
                setAppStatusDiv('Please select an app first.');
                return;
            }

            setAppStatusDiv(`Requesting install of ${app}...`);
            const out = await apiPost('/approvals/request', {
                kind: 'install_app',
                payload: { app, method: 'auto' },
            });

            if (out.status >= 400) {
                setAppStatusDiv(`Error: ${out.error || 'Failed to request install'}`);
            } else {
                const approval = out.body && out.body.approval ? out.body.approval : {};
                setAppStatusDiv(`Install request queued.\nApproval ID: ${approval.id || 'unknown'}\nApp: ${app}\n\nGo to the approval queue to approve.`);
                loadPending();
            }
        }

        async function requestAppUninstall() {
            const appSelector = document.getElementById('appSelector');
            const app = appSelector ? appSelector.value : '';
            if (!app) {
                setAppStatusDiv('Please select an app first.');
                return;
            }

            setAppStatusDiv(`Requesting uninstall of ${app}...`);
            const out = await apiPost('/approvals/request', {
                kind: 'uninstall_app',
                payload: { app },
            });

            if (out.status >= 400) {
                setAppStatusDiv(`Error: ${out.error || 'Failed to request uninstall'}`);
            } else {
                const approval = out.body && out.body.approval ? out.body.approval : {};
                setAppStatusDiv(`Uninstall request queued.\nApproval ID: ${approval.id || 'unknown'}\nApp: ${app}\n\nGo to the approval queue to approve.`);
                loadPending();
            }
        }

        function setAppStatusDiv(message) {
            const div = document.getElementById('appStatus');
            if (div) {
                div.textContent = message;
                div.style.display = 'block';
            }
        }

        async function generateTradeReviewArtifact() {
            const reviewer = getFieldValue(['#tradeReviewReviewer'], false);
            const strategyVersion = getFieldValue(['#tradeReviewVersion'], false);
            setTradeReviewStatus('Generating trade review artifact...');

            const out = await apiPost('/trade/review-artifact', {
                reviewer,
                strategy_version: strategyVersion,
            });

            if (out.status >= 400) {
                setTradeReviewStatus(`Error: ${out.body && out.body.error ? out.body.error : 'Failed to generate review artifact'}`);
                return;
            }

            const body = out.body || {};
            currentTradeReviewId = body.review_id || '';
            currentTradeReviewArtifacts = body;
            setTradeReviewStatus(
                `Review artifact generated.\n`
                + `Decision: ${body.auto_decision || 'unknown'}\n`
                + `Review markdown: ${body.review_markdown || 'n/a'}\n`
                + `Performance report: ${body.trade_performance_report || 'n/a'}`
            );
            setTradeReviewPreview(body.review_markdown_content || 'No review content returned.');
        }

        async function loadLatestTradeReviewArtifact() {
            const out = await apiGet('/trade/review-artifact/latest');
            if (out.status === 404) {
                return;
            }
            if (out.status >= 400) {
                setTradeReviewStatus(`Error: ${out.body && out.body.error ? out.body.error : 'Failed to load latest review artifact'}`);
                return;
            }

            const body = out.body || {};
            currentTradeReviewId = body.review_id || '';
            currentTradeReviewArtifacts = body;
            setTradeReviewStatus(
                `Latest review loaded.\n`
                + `Decision: ${body.auto_decision || 'unknown'}\n`
                + `Review markdown: ${body.review_markdown || 'n/a'}\n`
                + `Performance report: ${body.trade_performance_report || 'n/a'}`
            );
            setTradeReviewPreview(body.review_markdown_content || 'No review content returned.');
        }

        async function loadTradeReviewHistory() {
            const out = await apiGet('/trade/review-artifact/history?limit=5');
            const box = document.getElementById('tradeReviewHistory');
            if (!box) {
                return;
            }
            box.innerHTML = '';

            if (out.status >= 400) {
                const line = document.createElement('div');
                line.textContent = 'Unable to load review history.';
                box.appendChild(line);
                return;
            }

            const items = out.body && Array.isArray(out.body.items) ? out.body.items : [];
            if (items.length === 0) {
                const line = document.createElement('div');
                line.textContent = 'No saved reviews yet.';
                box.appendChild(line);
                return;
            }

            for (const item of items) {
                const button = document.createElement('button');
                button.className = 'ghost';
                button.style.textAlign = 'left';
                button.textContent = `${item.review_date || 'unknown date'} | ${item.auto_decision || 'unknown'} | ${item.reviewer || 'unassigned'} | trades: ${item.trade_count ?? 'n/a'} | ${item.strategy_version || 'n/a'}`;
                button.addEventListener('click', async () => {
                    const selected = await apiGet(`/trade/review-artifact/item?review_id=${encodeURIComponent(item.review_id || '')}`);
                    if (selected.status >= 400) {
                        setTradeReviewStatus('Error: Failed to load selected review.');
                        return;
                    }
                    const body = selected.body || {};
                    currentTradeReviewId = body.review_id || '';
                    currentTradeReviewArtifacts = body;
                    setTradeReviewStatus(
                        `Selected review loaded.\n`
                        + `Decision: ${body.auto_decision || 'unknown'}\n`
                        + `Review markdown: ${body.review_markdown || 'n/a'}\n`
                        + `Performance report: ${body.trade_performance_report || 'n/a'}`
                    );
                    setTradeReviewPreview(body.review_markdown_content || 'No review content returned.');
                });
                box.appendChild(button);
            }
        }

        function downloadTradeReviewArtifact() {
            if (!currentTradeReviewId) {
                setTradeReviewStatus('Error: Load or generate a review before downloading it.');
                return;
            }
            window.location.href = `/trade/review-artifact/download?review_id=${encodeURIComponent(currentTradeReviewId)}`;
        }

        function downloadTradeReviewSupportingArtifact(kind) {
            if (!currentTradeReviewId) {
                setTradeReviewStatus('Error: Load or generate a review before downloading artifacts.');
                return;
            }
            if (!currentTradeReviewArtifacts || !currentTradeReviewArtifacts[kind]) {
                setTradeReviewStatus(`Error: ${kind} is not available for the selected review.`);
                return;
            }
            window.location.href = `/trade/review-artifact/download-artifact?review_id=${encodeURIComponent(currentTradeReviewId)}&kind=${encodeURIComponent(kind)}`;
        }

        function setTradeReviewStatus(message) {
            const div = document.getElementById('tradeReviewStatus');
            if (div) {
                div.textContent = message;
                div.style.display = 'block';
            }
        }

        function setTradeReviewPreview(message) {
            const div = document.getElementById('tradeReviewPreview');
            if (div) {
                div.textContent = message;
                div.style.display = 'block';
            }
        }

        setInterval(tickDashboard, 4000);
        loadPending();
        loadLatestTradeReviewArtifact();
        loadTradeReviewHistory();
    </script>
</body>
</html>
"""


def _health_payload(config: Config) -> tuple[int, dict]:
    bus = EventBus(config.event_bus_db)
    runner = MonitorRunner(bus)
    register_configured_monitors(runner, config)

    event_bus_healthy = bus.healthcheck()
    chat_accounts = _chat_accounts(config)
    chat_configured = len(chat_accounts) > 0
    ai_ready = bool((config.get_secret("ANTHROPIC_API_KEY") or config.anthropic_api_key).strip())
    sources = [monitor.source for monitor in runner.monitors]
    monitor_status = {
        source: {
            "last_run_timestamp": None,
            "cumulative_event_count": 0,
        }
        for source in sources
    }

    payload = {
        "status": "ok" if event_bus_healthy else "degraded",
        "event_bus": {
            "healthy": event_bus_healthy,
            "db_path": str(config.event_bus_db),
        },
        "monitors": {
            "stopped": MonitorRunner.is_stopped(),
            "configured": len(sources),
            "sources": sources,
            "status": monitor_status,
        },
        "chat": {
            "configured": chat_configured,
            "accounts": len(chat_accounts),
        },
        "ai": {
            "provider": "anthropic",
            "ready": ai_ready,
        },
    }

    if event_bus_healthy:
        stats = runner.stats()
        payload["event_bus"].update(
            {
                "total_events": stats["total_events"],
                "unprocessed_events": stats["unprocessed_events"],
                "processed_events": stats["processed_events"],
            }
        )
        payload["monitors"]["status"] = stats["monitor_status"]

    return (200 if event_bus_healthy else 503), payload


def _render_ui_html(config: Config) -> str:
    drawdown_limit = config.trading_account_equity * (config.trading_daily_drawdown_kill_pct / 100.0)
    replacements = {
        "__TRADE_REVIEW_MIN_TRADING_DAYS__": html.escape(str(config.trading_review_min_trading_days)),
        "__TRADE_REVIEW_MIN_TRADES__": html.escape(str(config.trading_review_min_trades)),
        "__TRADE_REVIEW_MIN_WIN_RATE__": html.escape(f"{config.trading_review_min_win_rate:.4f}"),
        "__TRADE_REVIEW_MIN_PROFIT_FACTOR__": html.escape(f"{config.trading_review_min_profit_factor:.2f}"),
        "__TRADE_REVIEW_MIN_AVG_R_MULTIPLE__": html.escape(f"{config.trading_review_min_avg_r_multiple:.2f}"),
        "__TRADE_REVIEW_MAX_ANOMALIES__": html.escape(str(config.trading_review_max_anomalies)),
        "__TRADE_REVIEW_DRAWDOWN_LIMIT__": html.escape(f"{drawdown_limit:.2f}"),
    }
    rendered = UI_HTML
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered


def _chat_accounts(config: Config) -> dict[str, str]:
    """Resolve configured chat accounts from single-account and map settings."""
    accounts: dict[str, str] = {}
    if isinstance(config.chat_accounts, dict):
        for key, value in config.chat_accounts.items():
            if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                accounts[key.strip().lower()] = value.strip()
    if config.chat_account_id.strip() and config.chat_auth_token.strip():
        accounts[config.chat_account_id.strip().lower()] = config.chat_auth_token.strip()
    return accounts


def _chat_auth_ok(config: Config, account_id: str, token: str) -> bool:
    accounts = _chat_accounts(config)
    if not accounts:
        return False
    expected = accounts.get(account_id.strip().lower())
    if not expected:
        return False
    return hmac.compare_digest(expected, token or "")


def _hud_assets_version() -> str:
    """Compose a version stamp from mtimes of all live-reloadable assets."""
    paths: list[Path] = [Path(__file__).resolve()]
    for base in (REACT_HUD_DIR, COMMAND_CENTER_DIR, JARVIS_HOME_DIR):
        if base.exists():
            for child in base.iterdir():
                if child.is_file():
                    paths.append(child)
    parts: list[str] = []
    for p in paths:
        try:
            parts.append(f"{p.name}:{int(p.stat().st_mtime_ns)}")
        except OSError:
            continue
    return "|".join(sorted(parts))


OPS_WALLBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Jarvis Ops Wallboard</title>
    <style>
        :root {
            --bg: #05070d;
            --panel: rgba(9, 17, 31, 0.92);
            --panel-soft: rgba(9, 17, 31, 0.74);
            --line: rgba(98, 183, 255, 0.22);
            --line-strong: rgba(98, 183, 255, 0.5);
            --text: #e7f4ff;
            --muted: #95aec7;
            --active: #62b7ff;
            --accent: #ffd27d;
        }
        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: "Space Grotesk", "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at 14% 10%, rgba(98, 183, 255, 0.14), transparent 38%),
                radial-gradient(circle at 84% 78%, rgba(255, 210, 125, 0.08), transparent 34%),
                linear-gradient(180deg, #05070d, #07111d 52%, #05070d);
            color: var(--text);
        }
        .wrap {
            display: grid;
            grid-template-rows: auto 1fr;
            width: 100vw;
            height: 100vh;
        }
        .bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 16px;
            border-bottom: 1px solid var(--line);
            background: rgba(4, 8, 15, 0.94);
            backdrop-filter: blur(14px);
        }
        .bar-left,
        .bar-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .title-wrap {
            display: grid;
            gap: 2px;
        }
        .eyebrow {
            font-size: 10px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--muted);
        }
        .title {
            margin: 0;
            font-size: 14px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text);
        }
        .status-pill {
            border: 1px solid rgba(98, 183, 255, 0.3);
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 10px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #d8efff;
            background: rgba(7, 15, 28, 0.9);
        }
        .tabs {
            display: inline-flex;
            gap: 8px;
        }
        .tab-btn {
            border: 1px solid var(--line);
            background: rgba(8, 16, 28, 0.85);
            color: var(--muted);
            border-radius: 999px;
            padding: 7px 12px;
            cursor: pointer;
            font-size: 11px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .tab-btn.is-active {
            color: var(--text);
            border-color: var(--active);
            box-shadow: inset 0 0 0 1px rgba(98, 183, 255, 0.22), 0 0 16px rgba(98, 183, 255, 0.12);
        }
        .hint {
            color: var(--muted);
            font-size: 11px;
            white-space: nowrap;
        }
        .grid {
            display: grid;
            width: 100%;
            height: 100%;
            grid-template-columns: minmax(0, 1.5fr) minmax(360px, 0.92fr);
            grid-template-rows: minmax(0, 1fr) auto;
            grid-template-areas:
                "globe side"
                "dock side";
            gap: 12px;
            padding: 12px;
        }
        .panel,
        .side-panel,
        .dock,
        .hero-panel {
            position: relative;
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 18px;
            overflow: hidden;
            min-width: 0;
            min-height: 0;
            box-shadow: inset 0 0 40px rgba(98, 183, 255, 0.03), 0 18px 40px rgba(0, 0, 0, 0.22);
        }
        .hero-panel { grid-area: globe; }
        .side-panel {
            grid-area: side;
            display: grid;
            grid-template-rows: auto auto minmax(0, 1fr);
            gap: 12px;
            padding: 14px;
        }
        .dock {
            grid-area: dock;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            padding: 12px;
            background: var(--panel-soft);
        }
        .panel-frame,
        .hero-frame {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
        }
        .hero-frame {
            border-radius: 18px;
        }
        .hero-frame iframe {
            border: 0;
            width: 111.111%;
            height: 111.111%;
            background: #000;
            transform: scale(0.9);
            transform-origin: top left;
        }
        .panel-label {
            position: absolute;
            top: 12px;
            left: 12px;
            z-index: 2;
            border: 1px solid rgba(98, 183, 255, 0.42);
            background: rgba(6, 12, 24, 0.88);
            color: #cfeaff;
            border-radius: 999px;
            padding: 5px 11px;
            font-size: 10px;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            font-weight: 600;
            pointer-events: none;
            backdrop-filter: blur(4px);
        }
        .panel iframe {
            border: 0;
            width: 100%;
            height: 100%;
            background: #000;
        }
        .panel { display: none; }
        .panel.is-active { display: block; }
        .side-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            gap: 12px;
        }
        .side-title-wrap {
            display: grid;
            gap: 4px;
        }
        .side-title {
            margin: 0;
            font-size: 18px;
            line-height: 1;
            letter-spacing: 0.02em;
        }
        .side-copy {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.45;
            max-width: 34ch;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
        }
        .meta-card {
            border: 1px solid rgba(98, 183, 255, 0.14);
            border-radius: 14px;
            padding: 10px;
            background: rgba(7, 14, 26, 0.78);
        }
        .meta-kicker {
            font-size: 10px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
        }
        .meta-value {
            margin-top: 6px;
            font-size: 19px;
            line-height: 1;
            color: #eaf6ff;
        }
        .panel-stack {
            position: relative;
            min-height: 0;
            border: 1px solid rgba(98, 183, 255, 0.14);
            border-radius: 16px;
            background: rgba(5, 11, 20, 0.74);
            overflow: hidden;
        }
        .panel-stack .panel {
            position: absolute;
            inset: 0;
        }
        .panel-cc iframe {
            transform: scale(0.74);
            transform-origin: top left;
            width: 135.136%;
            height: 135.136%;
        }
        .panel-approvals iframe {
            transform: scale(0.82);
            transform-origin: top left;
            width: 121.952%;
            height: 121.952%;
        }
        .dock-card {
            border: 1px solid rgba(98, 183, 255, 0.14);
            border-radius: 14px;
            padding: 12px;
            background: rgba(6, 12, 22, 0.72);
            display: grid;
            gap: 8px;
            min-width: 0;
        }
        .dock-kicker {
            font-size: 10px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
        }
        .dock-title {
            font-size: 16px;
            line-height: 1.05;
            color: #eef8ff;
        }
        .dock-copy {
            font-size: 12px;
            line-height: 1.45;
            color: var(--muted);
        }
        .dock-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: auto;
        }
        .dock-link {
            border: 1px solid rgba(98, 183, 255, 0.2);
            border-radius: 999px;
            padding: 7px 12px;
            background: rgba(10, 19, 35, 0.86);
            color: #d9efff;
            text-decoration: none;
            font-size: 11px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .dock-link:hover {
            border-color: var(--line-strong);
        }
        .dock-link.is-primary {
            border-color: rgba(255, 210, 125, 0.28);
            color: #ffecce;
        }

        @media (max-width: 1100px), (max-height: 760px) {
            .hint { display: none; }
            .grid {
                grid-template-columns: 1fr;
                grid-template-rows: minmax(0, 1fr) auto auto;
                grid-template-areas:
                    "globe"
                    "side"
                    "dock";
                padding: 8px;
            }
            .side-panel {
                min-height: 420px;
            }
            .dock {
                grid-template-columns: 1fr;
            }
        }
        @media (max-width: 760px) {
            .bar {
                flex-wrap: wrap;
                align-items: center;
            }
            .bar-right {
                width: 100%;
                justify-content: space-between;
            }
            .meta-grid {
                grid-template-columns: 1fr;
            }
            .side-title {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="bar">
            <div class="bar-left">
                <div class="status-pill">Wallboard Live</div>
                <div class="title-wrap">
                    <div class="eyebrow">Single Screen Overview</div>
                    <h1 class="title">Jarvis Ops Wallboard</h1>
                </div>
            </div>
            <div class="bar-right">
                <div class="tabs" role="tablist" aria-label="Wallboard views">
                    <button class="tab-btn is-active" data-view="cc" type="button">Command Center</button>
                    <button class="tab-btn" data-view="approvals" type="button">Approvals</button>
                </div>
                <div class="hint">GLOBE stays primary • 1/2 switches side view</div>
            </div>
        </div>
        <div class="grid" id="wallboard-grid">
            <section class="hero-panel">
                <div class="panel-label">Strategic Globe</div>
                <div class="hero-frame">
                    <iframe src="/hud/react" title="Strategic Globe"></iframe>
                </div>
            </section>
            <aside class="side-panel">
                <div class="side-header">
                    <div class="side-title-wrap">
                        <div class="eyebrow">Focused Companion View</div>
                        <h2 class="side-title">Keep one system readable at a time</h2>
                        <div class="side-copy">The globe stays dominant. The right rail swaps between command controls and approvals so the page reads like a wallboard instead of three tiny websites.</div>
                    </div>
                    <div class="status-pill">Ops Mode</div>
                </div>
                <div class="meta-grid">
                    <div class="meta-card">
                        <div class="meta-kicker">Primary</div>
                        <div class="meta-value">Globe</div>
                    </div>
                    <div class="meta-card">
                        <div class="meta-kicker">Side Rail</div>
                        <div class="meta-value">1 live panel</div>
                    </div>
                    <div class="meta-card">
                        <div class="meta-kicker">Switch</div>
                        <div class="meta-value">1 / 2 keys</div>
                    </div>
                </div>
                <div class="panel-stack">
                    <section class="panel panel-cc is-active" data-view-panel="cc">
                        <div class="panel-label">Command Center</div>
                        <div class="panel-frame">
                            <iframe src="/hud/cc" title="Command Center"></iframe>
                        </div>
                    </section>
                    <section class="panel panel-approvals" data-view-panel="approvals">
                        <div class="panel-label">Approvals</div>
                        <div class="panel-frame">
                            <iframe src="/" title="Approvals"></iframe>
                        </div>
                    </section>
                </div>
            </aside>
            <section class="dock">
                <article class="dock-card">
                    <div class="dock-kicker">Primary Surface</div>
                    <div class="dock-title">Strategic Globe</div>
                    <div class="dock-copy">Use this for spatial awareness, threat focus, and feed overlays.</div>
                    <div class="dock-actions">
                        <a class="dock-link is-primary" href="/hud/react">Open Full View</a>
                    </div>
                </article>
                <article class="dock-card">
                    <div class="dock-kicker">Operations</div>
                    <div class="dock-title">Command Center</div>
                    <div class="dock-copy">Switch the side rail here when you need runtime controls, markets, and feed summaries.</div>
                    <div class="dock-actions">
                        <button class="tab-btn is-active" data-view="cc" type="button">Show In Rail</button>
                        <a class="dock-link" href="/hud/cc">Open Full View</a>
                    </div>
                </article>
                <article class="dock-card">
                    <div class="dock-kicker">Queue</div>
                    <div class="dock-title">Approvals</div>
                    <div class="dock-copy">Use the side rail for live approval handling when you need to act without leaving the wallboard.</div>
                    <div class="dock-actions">
                        <button class="tab-btn" data-view="approvals" type="button">Show In Rail</button>
                        <a class="dock-link" href="/">Open Full View</a>
                    </div>
                </article>
            </section>
        </div>
    </div>
    <script>
        (function () {
            var buttons = Array.from(document.querySelectorAll('.tab-btn[data-view]'));
            var panels = Array.from(document.querySelectorAll('[data-view-panel]'));
            function activate(view) {
                buttons.forEach(function (btn) {
                    btn.classList.toggle('is-active', btn.getAttribute('data-view') === view);
                });
                panels.forEach(function (panel) {
                    panel.classList.toggle('is-active', panel.getAttribute('data-view-panel') === view);
                });
            }
            buttons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    activate(btn.getAttribute('data-view'));
                });
            });
            window.addEventListener('keydown', function (event) {
                if (event.key === '1') activate('cc');
                if (event.key === '2') activate('approvals');
            });
        })();
    </script>
 </body>
</html>
"""


_LIVE_RELOAD_SNIPPET = """
<script>
(function () {
  var current = null;
  async function tick() {
    try {
      var r = await fetch('/hud/version', { cache: 'no-store' });
      if (!r.ok) return;
      var v = (await r.json()).version;
      if (current === null) { current = v; return; }
      if (v !== current) { location.reload(); }
    } catch (_) { /* ignore */ }
  }
  setInterval(tick, 1000);
  tick();
})();
</script>
"""


def _inject_live_reload(html_body: str) -> str:
    if "</body>" in html_body:
        return html_body.replace("</body>", _LIVE_RELOAD_SNIPPET + "</body>", 1)
    if "</html>" in html_body:
        return html_body.replace("</html>", _LIVE_RELOAD_SNIPPET + "</html>", 1)
    return html_body + _LIVE_RELOAD_SNIPPET


def _stop_sentinel_path() -> Path:
    return Path.home() / ".jarvis" / "stopped"


def _runtime_stop() -> dict[str, object]:
    sentinel = _stop_sentinel_path()
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    already_stopped = sentinel.exists()
    if not already_stopped:
        sentinel.write_text(str(int(datetime.now(timezone.utc).timestamp())), encoding="utf-8")
    return {
        "status": "stopped",
        "already_stopped": already_stopped,
        "sentinel": str(sentinel),
    }


def _runtime_resume() -> dict[str, object]:
    sentinel = _stop_sentinel_path()
    was_stopped = sentinel.exists()
    if was_stopped:
        sentinel.unlink()
    return {
        "status": "running",
        "was_stopped": was_stopped,
        "sentinel": str(sentinel),
    }


def _load_react_hud_asset(filename: str) -> tuple[str, str] | None:
    content_type = REACT_HUD_ASSETS.get(filename)
    if content_type is None:
        return None
    path = REACT_HUD_DIR / filename
    if not path.exists() or not path.is_file():
        return None
    return content_type, path.read_text(encoding="utf-8")


def _load_command_center_asset(filename: str) -> tuple[str, str] | None:
    content_type = COMMAND_CENTER_ASSETS.get(filename)
    if content_type is None:
        return None
    path = COMMAND_CENTER_DIR / filename
    if not path.exists() or not path.is_file():
        return None
    return content_type, path.read_text(encoding="utf-8")


def _load_jarvis_home_asset(filename: str) -> tuple[str, str] | None:
    content_type = JARVIS_HOME_ASSETS.get(filename)
    if content_type is None:
        return None
    path = JARVIS_HOME_DIR / filename
    if not path.exists() or not path.is_file():
        return None
    return content_type, path.read_text(encoding="utf-8")


def _payments_signature_ok(secret: str, raw_body: bytes, provided_sig: str) -> bool:
    if not secret.strip() or not provided_sig.strip():
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, digestmod="sha256").hexdigest()
    provided = provided_sig.strip()
    if provided.startswith("sha256="):
        provided = provided.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


def create_approval_api_server(
    config: Config,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> ThreadingHTTPServer:
    chat_brains: dict[str, object] = {}

    class ApprovalApiHandler(BaseHTTPRequestHandler):
        def _read_raw_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return b""
            return self.rfile.read(length)

        def _read_json(self, raw_body: bytes) -> dict:
            raw = raw_body.decode("utf-8")
            if not raw.strip():
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"_invalid_json": True}

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_html(self, status: int, html: str) -> None:
            data = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_xml(self, status: int, xml_body: str) -> None:
            data = xml_body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_markdown(self, status: int, markdown_body: str, filename: str) -> None:
            data = markdown_body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_bytes(self, status: int, data: bytes, content_type: str, filename: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_text(self, status: int, text: str, content_type: str) -> None:
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(200, _inject_live_reload(_render_ui_html(config)))
                return

            if parsed.path == "/hud/version":
                self._send(200, {"version": _hud_assets_version()})
                return

            if parsed.path in ("/hud/ops", "/hud/ops/", "/hud/wallboard", "/hud/wallboard/"):
                self._send_html(200, _inject_live_reload(OPS_WALLBOARD_HTML))
                return

            if parsed.path in ("/hud/react", "/hud/react/"):
                asset = _load_react_hud_asset("index.html")
                if asset is None:
                    self._send(404, {"error": "react hud viewport unavailable"})
                    return
                content_type, body = asset
                self._send_text(200, _inject_live_reload(body), content_type)
                return

            if parsed.path.startswith("/hud/react/"):
                filename = parsed.path[len("/hud/react/") :]
                asset = _load_react_hud_asset(filename)
                if asset is None:
                    self._send(404, {"error": "react hud asset unavailable"})
                    return
                content_type, body = asset
                self._send_text(200, body, content_type)
                return

            if parsed.path in ("/hud/cc", "/hud/cc/"):
                asset = _load_command_center_asset("index.html")
                if asset is None:
                    self._send(404, {"error": "command center unavailable"})
                    return
                content_type, body = asset
                self._send_text(200, _inject_live_reload(body), content_type)
                return

            if parsed.path.startswith("/hud/cc/"):
                filename = parsed.path[len("/hud/cc/") :]
                asset = _load_command_center_asset(filename)
                if asset is None:
                    self._send(404, {"error": "command center asset unavailable"})
                    return
                content_type, body = asset
                self._send_text(200, body, content_type)
                return

            if parsed.path in ("/hud/home", "/hud/home/"):
                asset = _load_jarvis_home_asset("index.html")
                if asset is None:
                    self._send(404, {"error": "jarvis home unavailable"})
                    return
                content_type, body = asset
                self._send_text(200, _inject_live_reload(body), content_type)
                return

            if parsed.path.startswith("/hud/home/"):
                filename = parsed.path[len("/hud/home/") :]
                asset = _load_jarvis_home_asset(filename)
                if asset is None:
                    self._send(404, {"error": "jarvis home asset unavailable"})
                    return
                content_type, body = asset
                self._send_text(200, body, content_type)
                return

            if parsed.path == "/health":
                status, payload = _health_payload(config)
                self._send(status, payload)
                return

            if parsed.path == "/approvals/pending":
                query = parse_qs(parsed.query)
                limit_raw = query.get("limit", ["100"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    self._send(400, {"error": "invalid limit"})
                    return
                service = ApprovalService(config)
                self._send(200, {"items": service.list_pending(limit=limit)})
                return

            if parsed.path == "/chat/history":
                if not _chat_accounts(config):
                    self._send(503, {"error": "chat inbound is not configured"})
                    return

                query = parse_qs(parsed.query)
                account_id = str(query.get("account_id", [""])[0]).strip().lower()
                token = str(query.get("token", [""])[0])
                limit_raw = query.get("limit", ["20"])[0]

                if not account_id:
                    self._send(400, {"error": "account_id is required"})
                    return
                if not token:
                    self._send(400, {"error": "token is required"})
                    return
                if not _chat_auth_ok(config, account_id, token):
                    self._send(401, {"error": "unauthorized"})
                    return

                try:
                    limit = int(limit_raw)
                except ValueError:
                    self._send(400, {"error": "invalid limit"})
                    return
                if limit <= 0 or limit > 200:
                    self._send(400, {"error": "limit must be between 1 and 200"})
                    return

                scan_limit = min(max(limit * 10, 100), 500)
                events = EventBus(config.event_bus_db).recent(limit=scan_limit, kind="chat_message")
                items_newest: list[dict[str, object]] = []
                for event in events:
                    if str(event.payload.get("account_id", "")).strip().lower() != account_id:
                        continue
                    text = str(event.payload.get("text", "")).strip()
                    if not text:
                        continue
                    items_newest.append(
                        {
                            "event_id": event.id,
                            "timestamp": event.timestamp,
                            "source": event.source,
                            "text": text,
                        }
                    )
                    if len(items_newest) >= limit:
                        break

                self._send(200, {"items": list(reversed(items_newest))})
                return

            if parsed.path == "/trade/review-artifact/latest":
                payload = load_latest_trade_review_artifact()
                if payload is None:
                    self._send(404, {"error": "trade review artifact not found"})
                    return
                self._send(200, payload)
                return

            if parsed.path == "/trade/review-artifact/item":
                query = parse_qs(parsed.query)
                review_id = str(query.get("review_id", [""])[0]).strip()
                if not review_id:
                    self._send(400, {"error": "review_id is required"})
                    return
                payload = load_trade_review_artifact(review_id)
                if payload is None:
                    self._send(404, {"error": "trade review artifact not found"})
                    return
                self._send(200, payload)
                return

            if parsed.path == "/trade/review-artifact/download":
                query = parse_qs(parsed.query)
                review_id = str(query.get("review_id", [""])[0]).strip()
                if not review_id:
                    self._send(400, {"error": "review_id is required"})
                    return
                payload = load_trade_review_artifact(review_id)
                if payload is None:
                    self._send(404, {"error": "trade review artifact not found"})
                    return
                review_markdown = str(payload.get("review_markdown_content", ""))
                filename = Path(str(payload.get("review_markdown", "review.md"))).name
                self._send_markdown(200, review_markdown, filename)
                return

            if parsed.path == "/trade/review-artifact/download-artifact":
                query = parse_qs(parsed.query)
                review_id = str(query.get("review_id", [""])[0]).strip()
                kind = str(query.get("kind", [""])[0]).strip()
                if not review_id:
                    self._send(400, {"error": "review_id is required"})
                    return
                if kind not in {"trade_performance_report", "trade_replay_report", "audit_export"}:
                    self._send(400, {"error": "invalid artifact kind"})
                    return
                payload = load_trade_review_artifact(review_id)
                if payload is None:
                    self._send(404, {"error": "trade review artifact not found"})
                    return
                file_path = str(payload.get(kind, "")).strip()
                if not file_path:
                    self._send(404, {"error": "supporting artifact not found"})
                    return
                try:
                    with open(file_path, "rb") as handle:
                        data = handle.read()
                except OSError:
                    self._send(404, {"error": "supporting artifact not found"})
                    return
                filename = Path(file_path).name
                content_type = "application/json; charset=utf-8"
                if kind == "audit_export":
                    content_type = "application/x-ndjson; charset=utf-8"
                self._send_bytes(200, data, content_type, filename)
                return

            if parsed.path == "/trade/review-artifact/history":
                query = parse_qs(parsed.query)
                limit_raw = query.get("limit", ["5"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    self._send(400, {"error": "invalid limit"})
                    return
                if limit <= 0 or limit > 20:
                    self._send(400, {"error": "limit must be between 1 and 20"})
                    return
                self._send(200, {"items": list_recent_trade_review_artifacts(limit=limit)})
                return

            if parsed.path == "/hud/news":
                query = parse_qs(parsed.query)
                source = str(query.get("source", ["reuters"])[0]).strip().lower()
                limit_raw = query.get("limit", ["6"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    self._send(400, {"error": "invalid limit"})
                    return
                if limit <= 0 or limit > 20:
                    self._send(400, {"error": "limit must be between 1 and 20"})
                    return
                payload = _latest_news_payload(source, limit)
                if payload.get("error"):
                    self._send(400, payload)
                    return
                self._send(200, payload)
                return

            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            raw_body = self._read_raw_body()

            if parsed.path == "/runtime/stop":
                self._send(200, _runtime_stop())
                return

            if parsed.path == "/runtime/resume":
                self._send(200, _runtime_resume())
                return

            if parsed.path == "/chat/twilio":
                if not _chat_accounts(config):
                    self._send(503, {"error": "chat inbound is not configured"})
                    return

                query = parse_qs(parsed.query)
                form = parse_qs(raw_body.decode("utf-8", errors="ignore"))
                response_format = str(query.get("response_format", [""])[0]).strip().lower()
                wants_json = response_format == "json"

                account_id = str(
                    (query.get("account_id", [""])[0] or form.get("account_id", [""])[0])
                ).strip().lower()
                token = str(
                    (query.get("token", [""])[0] or form.get("token", [""])[0])
                )

                if not account_id:
                    self._send(400, {"error": "account_id is required"})
                    return
                if not token:
                    self._send(400, {"error": "token is required"})
                    return
                if not _chat_auth_ok(config, account_id, token):
                    self._send(401, {"error": "unauthorized"})
                    return

                bot_payload = {
                    "user": str(form.get("From", [""])[0]),
                    "chat_id": str(form.get("To", [""])[0]),
                    "body": str(form.get("Body", [""])[0]),
                    "message_id": str(form.get("MessageSid", [""])[0]),
                }
                parsed_chat = build_chat_registry().parse("bot", bot_payload)
                if parsed_chat.get("error"):
                    self._send(400, {"error": str(parsed_chat.get("error"))})
                    return

                text = str(parsed_chat.get("text") or "").strip()
                sms_command = parse_sms_command(text)

                event = RuntimeEventEnvelope(
                    kind="chat_message",
                    source="chat_twilio_sms",
                    payload={
                        **parsed_chat,
                        "account_id": account_id,
                        "sms_command": sms_command,
                    },
                )
                EventBus(config.event_bus_db).emit(event)

                if not text:
                    if wants_json:
                        payload_out = {"status": "accepted", "event_id": event.id}
                        if sms_command.get("recognized"):
                            payload_out["sms_command"] = sms_command
                        self._send(200, payload_out)
                    else:
                        self._send_xml(
                            200,
                            (
                                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                                "<Response><Message>Message received.</Message></Response>"
                            ),
                        )
                    return

                reply = ""
                reply_error = ""
                try:
                    brain = chat_brains.get(account_id)
                    if brain is None:
                        brain = build_brain_from_config(config)
                        chat_brains[account_id] = brain
                    reply = str(brain.turn(text))  # type: ignore[union-attr]
                except Exception as exc:  # noqa: BLE001
                    reply_error = f"chat_reply_unavailable: {exc.__class__.__name__}"

                payload_out = {
                    "status": "accepted",
                    "event_id": event.id,
                }
                if sms_command.get("recognized"):
                    payload_out["sms_command"] = sms_command
                if reply:
                    payload_out["reply"] = reply
                if reply_error:
                    payload_out["reply_error"] = reply_error

                if wants_json:
                    self._send(200, payload_out)
                else:
                    twiml_text = reply or "Message received."
                    safe_text = html.escape(twiml_text, quote=False)
                    self._send_xml(
                        200,
                        (
                            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                            f"<Response><Message>{safe_text}</Message></Response>"
                        ),
                    )
                return

            if parsed.path == "/webhooks/twilio":
                if not config.twilio_webhook_token.strip():
                    self._send(503, {"error": "twilio webhook bridge is not configured"})
                    return

                query = parse_qs(parsed.query)
                form = parse_qs(raw_body.decode("utf-8", errors="ignore"))
                token = str(
                    (query.get("token", [""])[0] or form.get("token", [""])[0])
                ).strip()
                if not token:
                    self._send(400, {"error": "token is required"})
                    return
                if token != config.twilio_webhook_token:
                    self._send(401, {"error": "unauthorized"})
                    return

                message_sid = str(form.get("MessageSid", [""])[0]).strip()
                call_sid = str(form.get("CallSid", [""])[0]).strip()
                event_type = "unknown"
                if message_sid:
                    event_type = "sms"
                elif call_sid:
                    event_type = "voice_call"

                event = RuntimeEventEnvelope(
                    kind="twilio_webhook",
                    source="twilio_webhook_bridge",
                    payload={
                        "event_type": event_type,
                        "account_sid": str(form.get("AccountSid", [""])[0]).strip(),
                        "message_sid": message_sid,
                        "call_sid": call_sid,
                        "from": str(form.get("From", [""])[0]).strip(),
                        "to": str(form.get("To", [""])[0]).strip(),
                        "body": str(form.get("Body", [""])[0]),
                        "sms_status": str(form.get("SmsStatus", [""])[0]).strip(),
                        "call_status": str(form.get("CallStatus", [""])[0]).strip(),
                        "recording_sid": str(form.get("RecordingSid", [""])[0]).strip(),
                        "recording_url": str(form.get("RecordingUrl", [""])[0]).strip(),
                        "raw_form": {key: values[0] if values else "" for key, values in form.items()},
                    },
                )
                EventBus(config.event_bus_db).emit(event)

                self._send(200, {"status": "accepted", "event_id": event.id})
                return

            body = self._read_json(raw_body)
            if body.get("_invalid_json"):
                self._send(400, {"error": "invalid json"})
                return

            if parsed.path == "/approvals/dispatch":
                limit = body.get("limit", 100)
                if not isinstance(limit, int):
                    self._send(400, {"error": "limit must be an integer"})
                    return
                service = ApprovalService(config)
                summary = service.dispatch(limit=limit)
                self._send(200, asdict(summary))
                return

            if parsed.path == "/trade/review-artifact":
                reviewer = body.get("reviewer", "")
                strategy_version = body.get("strategy_version", "")
                output_file = body.get("output")

                if not isinstance(reviewer, str):
                    self._send(400, {"error": "reviewer must be a string"})
                    return
                if not isinstance(strategy_version, str):
                    self._send(400, {"error": "strategy_version must be a string"})
                    return
                if output_file is not None and not isinstance(output_file, str):
                    self._send(400, {"error": "output must be a string"})
                    return

                try:
                    payload = generate_trade_review_artifact(
                        config,
                        output_file=output_file,
                        reviewer=reviewer,
                        strategy_version=strategy_version,
                    )
                except Exception as exc:  # noqa: BLE001
                    self._send(
                        500,
                        {
                            "error": "trade review artifact generation failed",
                            "detail": f"{exc.__class__.__name__}: {exc}",
                        },
                    )
                    return

                self._send(200, payload)
                return

            if parsed.path == "/chat/inbound":
                if not _chat_accounts(config):
                    self._send(503, {"error": "chat inbound is not configured"})
                    return

                account_id = str(body.get("account_id", "")).strip().lower()
                token = str(body.get("token", ""))
                source = str(body.get("source", "ios_shortcuts")).strip().lower() or "ios_shortcuts"

                if not account_id:
                    self._send(400, {"error": "account_id is required"})
                    return
                if not token:
                    self._send(400, {"error": "token is required"})
                    return
                if not _chat_auth_ok(config, account_id, token):
                    self._send(401, {"error": "unauthorized"})
                    return

                payload = body.get("payload")
                if payload is None:
                    text = body.get("text", "")
                    payload = {"text": text} if isinstance(text, str) else {}
                if not isinstance(payload, dict):
                    self._send(400, {"error": "payload must be an object"})
                    return

                parsed_chat = build_chat_registry().parse(source, payload)
                if parsed_chat.get("error"):
                    self._send(400, {"error": str(parsed_chat.get("error"))})
                    return

                event = RuntimeEventEnvelope(
                    kind="chat_message",
                    source=f"chat_{source}",
                    payload={
                        **parsed_chat,
                        "account_id": account_id,
                    },
                )
                EventBus(config.event_bus_db).emit(event)

                text = str(parsed_chat.get("text") or "").strip()
                if not text:
                    self._send(202, {"status": "accepted", "event_id": event.id})
                    return

                reply = ""
                reply_error = ""
                try:
                    brain = chat_brains.get(account_id)
                    if brain is None:
                        brain = build_brain_from_config(config)
                        chat_brains[account_id] = brain
                    reply = str(brain.turn(text))  # type: ignore[union-attr]
                except Exception as exc:  # noqa: BLE001
                    reply_error = f"chat_reply_unavailable: {exc.__class__.__name__}"

                payload_out = {
                    "status": "accepted",
                    "event_id": event.id,
                }
                if reply:
                    payload_out["reply"] = reply
                if reply_error:
                    payload_out["reply_error"] = reply_error

                self._send(202, payload_out)
                return

            if parsed.path == "/payments/reconcile":
                if not config.payments_webhook_secret.strip():
                    self._send(503, {"error": "payments reconciliation webhook is not configured"})
                    return

                provided_sig = self.headers.get("X-Jarvis-Signature", "")
                if not _payments_signature_ok(config.payments_webhook_secret, raw_body, provided_sig):
                    self._send(401, {"error": "invalid signature"})
                    return

                provider = str(body.get("provider", "")).strip().lower() or "stripe"
                event_id = str(body.get("event_id", "")).strip()
                currency = str(body.get("currency", "")).strip().upper()
                merchant = str(body.get("merchant", "")).strip()
                external_txid = str(
                    body.get("external_txid")
                    or body.get("txid")
                    or body.get("charge_id")
                    or ""
                ).strip()

                amount = body.get("amount")
                if not event_id:
                    self._send(400, {"error": "event_id is required"})
                    return
                if not isinstance(amount, (int, float)) or amount <= 0:
                    self._send(400, {"error": "amount must be positive number"})
                    return
                if not currency:
                    self._send(400, {"error": "currency is required"})
                    return
                if not external_txid:
                    self._send(400, {"error": "external_txid (or txid/charge_id) is required"})
                    return

                ledger = PaymentsBudgetLedger(config.payments_budget_db)
                matched_internal_txid = ledger.find_internal_txid_by_external_txid(external_txid) or ""
                reconciliation_status = "matched" if matched_internal_txid else "unexpected"

                inserted = ledger.record_reconciliation_event(
                    ts=datetime.now(timezone.utc),
                    provider=provider,
                    event_id=event_id,
                    external_txid=external_txid,
                    amount=float(amount),
                    currency=currency,
                    merchant=merchant,
                    status=reconciliation_status,
                    matched_internal_txid=matched_internal_txid,
                    raw_payload_json=json.dumps(body, sort_keys=True),
                )
                if not inserted:
                    self._send(409, {"error": "duplicate reconciliation event"})
                    return

                alert_approval_id = ""
                if reconciliation_status == "unexpected":
                    alert_service = ApprovalService(config)
                    alert_payload = {
                        "channel": config.event_alert_channel,
                        "recipient": config.event_alert_recipient,
                        "subject": "Unexpected payment charge detected",
                        "body": (
                            f"Unexpected {currency} charge {external_txid} "
                            f"for {float(amount):.2f}"
                            + (f" at {merchant}" if merchant else "")
                            + ". No matching internal payment proposal was found."
                        ),
                        "metadata": {
                            "source": "payments_reconciliation",
                            "event_id": event_id,
                            "external_txid": external_txid,
                            "provider": provider,
                        },
                    }
                    alert_env = ApprovalEnvelope(
                        action="alert_unexpected_charge",
                        reason="no matching internal payment proposal",
                        budget_impact=float(amount),
                        risk_tier="high",
                    )
                    alert_approval_id = alert_service.request(
                        "message_send",
                        alert_payload,
                        envelope=alert_env,
                    )

                event = RuntimeEventEnvelope(
                    kind="payment_reconciliation",
                    source=f"payments_{provider}",
                    payload={
                        "event_id": event_id,
                        "external_txid": external_txid,
                        "amount": float(amount),
                        "currency": currency,
                        "merchant": merchant,
                        "status": reconciliation_status,
                        "matched_internal_txid": matched_internal_txid,
                        "alert_approval_id": alert_approval_id,
                    },
                )
                EventBus(config.event_bus_db).emit(event)
                self._send(
                    202,
                    {
                        "status": reconciliation_status,
                        "matched": bool(matched_internal_txid),
                        "event_id": event_id,
                        "alert_approval_id": alert_approval_id,
                    },
                )
                return

            parts = parsed.path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "approvals":
                approval_id = parts[1]
                action_name = parts[2]
                reason = body.get("reason", "")
                if not isinstance(reason, str):
                    self._send(400, {"error": "reason must be a string"})
                    return

                service = ApprovalService(config)
                if action_name == "approve":
                    ok = service.approve(approval_id, reason=reason)
                    if ok:
                        self._send(200, {"status": "approved", "approval_id": approval_id})
                    else:
                        self._send(404, {"error": "approval not found or not pending"})
                    return
                if action_name == "reject":
                    ok = service.reject(approval_id, reason=reason)
                    if ok:
                        self._send(200, {"status": "rejected", "approval_id": approval_id})
                    else:
                        self._send(404, {"error": "approval not found or not pending"})
                    return
                if action_name == "edit":
                    payload = body.get("payload")
                    if payload is not None and not isinstance(payload, dict):
                        self._send(400, {"error": "payload must be an object"})
                        return

                    try:
                        env = ApprovalEnvelope(
                            action=body.get("action", ""),
                            reason=reason,
                            budget_impact=body.get("budget_impact", 0.0),
                            ttl_seconds=body.get("ttl_seconds", 0),
                            risk_tier=body.get("risk_tier", "medium"),
                        )
                    except (TypeError, ValueError):
                        self._send(
                            400,
                            {
                                "error": (
                                    "invalid edit envelope values "
                                    "(budget_impact/ttl_seconds/risk_tier)"
                                )
                            },
                        )
                        return
                    ok = service.edit(approval_id, payload=payload, envelope=env)
                    if ok:
                        self._send(200, {"status": "edited", "approval_id": approval_id})
                    else:
                        self._send(404, {"error": "approval not found or not pending"})
                    return

            self._send(404, {"error": "not found"})

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            # Keep test and local CLI output clean.
            return

    return ThreadingHTTPServer((host, port), ApprovalApiHandler)
