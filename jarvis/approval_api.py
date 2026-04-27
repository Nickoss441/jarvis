"""Minimal HTTP API surface for approval operations."""
from dataclasses import asdict
from datetime import datetime, timezone
import html
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


UI_HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Jarvis Approvals</title>
    <style>
        :root {
            --bg-0: #070b13;
            --bg-1: #0f1524;
            --glass: rgba(16, 28, 49, 0.52);
            --glass-strong: rgba(11, 20, 37, 0.74);
            --line: rgba(98, 167, 255, 0.26);
            --line-bright: rgba(117, 196, 255, 0.7);
            --text: #e8f3ff;
            --muted: #9ab0cf;
            --accent: #3ea8ff;
            --alert: #ff5f72;
            --ok: #1ecf8f;
            --gold: #f2c66b;
        }
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at 20% 10%, rgba(62, 168, 255, 0.18), transparent 40%),
                radial-gradient(circle at 80% 80%, rgba(255, 95, 114, 0.12), transparent 35%),
                linear-gradient(130deg, var(--bg-0), var(--bg-1));
            overflow-x: hidden;
        }
        .ambient-grid {
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.22;
            background-image:
                linear-gradient(rgba(97, 150, 224, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(97, 150, 224, 0.1) 1px, transparent 1px);
            background-size: 44px 44px;
            mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
        }
        .wrap {
            max-width: 1320px;
            margin: 26px auto;
            padding: 0 16px 28px;
        }
        .hud {
            position: relative;
            display: grid;
            grid-template-columns: minmax(260px, 1fr) minmax(300px, 1.2fr) minmax(260px, 1fr);
            gap: 14px;
            align-items: start;
        }
        .panel {
            background: var(--glass);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px;
            backdrop-filter: blur(14px);
            box-shadow: 0 12px 40px rgba(2, 9, 19, 0.42);
            animation: panel-in 460ms ease both;
        }
        .panel h3 {
            margin: 0;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
        }
        .panel .sub {
            margin-top: 6px;
            color: var(--muted);
            font-size: 12px;
        }
        .stack {
            display: grid;
            gap: 14px;
        }
        .center-hub {
            position: relative;
            min-height: 660px;
            overflow: hidden;
            background:
                radial-gradient(circle at center, rgba(53, 110, 202, 0.26), rgba(8, 15, 30, 0.02) 65%),
                var(--glass-strong);
        }
        .title {
            margin: 0;
            font-family: "Chakra Petch", "Space Grotesk", sans-serif;
            font-size: 30px;
            font-weight: 600;
            letter-spacing: 0.04em;
        }
        .muted {
            margin: 8px 0 12px;
            color: var(--muted);
            font-size: 14px;
        }
        .globe-wrap {
            position: relative;
            width: min(390px, 82vw);
            height: min(390px, 82vw);
            margin: 22px auto 10px;
        }
        .globe {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background:
                radial-gradient(circle at 32% 28%, rgba(115, 198, 255, 0.62), rgba(29, 68, 143, 0.24) 38%, rgba(9, 17, 34, 0.95) 72%),
                repeating-linear-gradient(180deg, rgba(140, 205, 255, 0.18), rgba(140, 205, 255, 0.18) 2px, transparent 2px, transparent 10px);
            border: 1px solid rgba(127, 203, 255, 0.56);
            box-shadow:
                0 0 0 1px rgba(66, 139, 222, 0.22),
                0 0 46px rgba(49, 161, 255, 0.38),
                inset -42px -38px 65px rgba(0, 0, 0, 0.56);
            animation: spin 28s linear infinite;
        }
        .orbit {
            position: absolute;
            inset: -16px;
            border: 1px dashed rgba(115, 196, 255, 0.4);
            border-radius: 50%;
            animation: pulse 3.2s ease-in-out infinite;
        }
        .poi {
            position: absolute;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--alert);
            box-shadow: 0 0 0 0 rgba(255, 95, 114, 0.72);
            animation: ping 2s infinite;
        }
        .poi.p1 { top: 42%; left: 68%; }
        .poi.p2 { top: 27%; left: 45%; background: var(--gold); box-shadow: 0 0 0 0 rgba(242, 198, 107, 0.72); }
        .poi.p3 { top: 62%; left: 36%; background: var(--accent); box-shadow: 0 0 0 0 rgba(62, 168, 255, 0.72); }
        .connector-layer {
            position: absolute;
            inset: 0;
            pointer-events: none;
            opacity: 0.74;
        }
        .summary-bar {
            margin-top: 14px;
            padding: 10px 12px;
            border: 1px solid var(--line);
            border-radius: 10px;
            color: #d0e8ff;
            font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
            font-size: 12px;
            background: rgba(14, 26, 46, 0.55);
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .metric {
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 10px;
            background: rgba(8, 16, 29, 0.5);
        }
        .metric .label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
        }
        .metric .value {
            margin-top: 8px;
            font-size: 24px;
            font-weight: 700;
            line-height: 1;
            font-family: "Chakra Petch", "Space Grotesk", sans-serif;
        }
        .spark {
            width: 100%;
            height: 64px;
            margin-top: 8px;
            border-radius: 10px;
            border: 1px solid rgba(108, 175, 255, 0.28);
            background: rgba(12, 22, 40, 0.48);
        }
        .toolbar {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }
        button {
            border: 1px solid var(--line);
            background: rgba(13, 28, 52, 0.7);
            color: var(--text);
            border-radius: 9px;
            padding: 8px 12px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
        }
        button:hover {
            transform: translateY(-1px);
            border-color: var(--line-bright);
        }
        button.primary { background: linear-gradient(135deg, #1e7fff, #36c3ff); border-color: rgba(158, 216, 255, 0.7); color: #061322; }
        button.danger { background: linear-gradient(135deg, #de415f, #ff7386); border-color: rgba(255, 157, 173, 0.6); }
        button.ok { background: linear-gradient(135deg, #17b67e, #39e0a4); border-color: rgba(164, 255, 222, 0.6); color: #062417; }
        select, input, textarea {
            border: 1px solid var(--line);
            background: rgba(13, 28, 52, 0.7);
            color: var(--text);
            border-radius: 9px;
            padding: 8px 10px;
            font-weight: 500;
            font-family: "Space Grotesk", "Avenir Next", sans-serif;
        }
        select:hover, input:hover, textarea:hover {
            border-color: var(--line-bright);
        }
        select:focus, input:focus, textarea:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(62, 168, 255, 0.18);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 10px;
            background: rgba(8, 17, 31, 0.42);
            border-radius: 12px;
            overflow: hidden;
        }
        th, td {
            border-top: 1px solid rgba(95, 155, 232, 0.24);
            padding: 9px 8px;
            text-align: left;
            vertical-align: top;
        }
        th {
            color: #b9d7ff;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            background: rgba(10, 24, 45, 0.65);
        }
        td code {
            font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
            background: rgba(18, 36, 62, 0.9);
            color: #c6e6ff;
            padding: 2px 5px;
            border-radius: 5px;
            font-size: 11px;
        }
        #status,
        #chatStatus {
            margin-top: 10px;
            padding: 10px;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: rgba(9, 20, 38, 0.7);
            white-space: pre-wrap;
            font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
            font-size: 12px;
            min-height: 26px;
        }
        .chat {
            margin-top: 16px;
            border-top: 1px solid rgba(95, 155, 232, 0.24);
            padding-top: 14px;
        }
        .chat h2 {
            margin: 0;
            font-size: 20px;
            font-family: "Chakra Petch", "Space Grotesk", sans-serif;
            font-weight: 600;
            letter-spacing: 0.03em;
        }
        .row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .field {
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 180px;
            flex: 1;
        }
        .field label {
            color: var(--muted);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        .field input,
        .field textarea {
            border: 1px solid rgba(95, 155, 232, 0.35);
            border-radius: 9px;
            padding: 8px 10px;
            font: inherit;
            color: var(--text);
            background: rgba(7, 16, 31, 0.75);
        }
        .field textarea {
            min-height: 92px;
            resize: vertical;
        }
        #chatTranscript {
            margin-top: 10px;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: rgba(7, 15, 29, 0.74);
            padding: 10px;
            max-height: 240px;
            overflow-y: auto;
        }
        .chat-line {
            margin: 0 0 8px 0;
            padding: 8px;
            border-radius: 8px;
            white-space: pre-wrap;
            line-height: 1.35;
            font-size: 14px;
        }
        .chat-user { background: rgba(35, 88, 160, 0.35); border: 1px solid rgba(109, 173, 255, 0.4); }
        .chat-agent { background: rgba(16, 96, 80, 0.4); border: 1px solid rgba(113, 235, 191, 0.4); }
        .chat-error { background: rgba(133, 33, 50, 0.38); border: 1px solid rgba(255, 124, 146, 0.5); }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes ping {
            0% { transform: scale(1); box-shadow: 0 0 0 0 currentColor; }
            70% { transform: scale(1.15); box-shadow: 0 0 0 14px rgba(255, 95, 114, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 95, 114, 0); }
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.35; transform: scale(1); }
            50% { opacity: 0.9; transform: scale(1.02); }
        }
        @keyframes panel-in {
            from { opacity: 0; transform: translateY(12px) scale(0.99); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        @media (max-width: 1100px) {
            .hud {
                grid-template-columns: 1fr;
            }
            .center-hub {
                min-height: auto;
            }
            .globe-wrap {
                width: min(320px, 82vw);
                height: min(320px, 82vw);
            }
        }
    </style>
</head>
<body>
    <div class="ambient-grid"></div>
    <div class="wrap">
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

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(200, _render_ui_html(config))
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

            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            raw_body = self._read_raw_body()

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
