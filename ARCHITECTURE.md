# Jarvis-Style Personal Agent — Architecture

A design for an autonomous, voice-first personal agent that monitors data streams, reasons over them, and takes real-world actions — including bounded financial actions, outbound phone calls, and smart-home control — under a strict approval and budget regime.

This document covers the module breakdown, tech stack, a worked end-to-end example, security model, and a phased rollout plan. It is intended to be reviewed before any code is written.

---

## 1. Design principles

Five rules shape every module decision below.

**Hard limits live outside the agent.** Any limit that matters (spending caps, trade size, network access) is enforced by an external system that the agent cannot reason its way around — Visa for spend, the broker for trade size, the OS firewall for network. The agent's own logic is treated as a soft layer that can be jailbroken, prompt-injected, or simply confused.

**Tiered autonomy.** Tools are split into two tiers. *Open* tools (web search, smart home, reading email, drafting) the agent uses freely. *Gated* tools (payments, trades, outbound calls, shell execution, sending messages) always route through an approval surface — push notification, SMS, or in-app — even if the approval is one tap.

**Disclosure by default.** When the agent acts as you to other humans (calls, emails, messages), the script identifies it as an AI acting on your behalf. This is legally required in most jurisdictions you care about (EU AI Act Art. 50, California SB 1001, Utah AI policy, growing list of others) and is also what makes the agent successful — businesses increasingly hang up on undisclosed AI.

**Append-only audit.** Every observation, decision, tool call, approval, and external response is written to an immutable log. This is what makes debugging tractable, what gives you legal recourse if something charges you twice, and what lets you replay a session.

**Reversibility first.** The agent prefers reversible actions. Drafts before sends. Holds before charges. Limit orders before market orders. Reservations it can cancel before deposits it cannot.

---

## 2. Module breakdown

### 2.1 Perception layer

Three input modalities feeding the brain.

**Voice.** A wake-word listener runs continuously on-device (openWakeWord, free; or Picovoice Porcupine, free for personal use). On wake, audio streams to a local Whisper instance (faster-whisper, base or small model — runs comfortably on a modern laptop CPU, faster on GPU/Apple Silicon). For lower latency you can use OpenAI's Realtime API or Deepgram, at a modest per-minute cost.

**Monitors.** Background workers that pull or subscribe to data streams the agent should react to. Examples: an RSS poller for news feeds, a webhook receiver for IFTTT/Zapier-style triggers, a market-data subscription (read-only — Alpha Vantage, Polygon, or your broker's quote feed), a filesystem watcher for a "drop zone" folder, a calendar poll for upcoming events. Each monitor pushes structured events onto a single event bus (Redis Streams, NATS, or simply SQLite + a polling worker for a small setup).

**Chat / API.** A direct text channel — a web UI, an iOS Shortcuts endpoint, a Telegram or Signal bot. This is the manual override and the receipt for approval prompts.

### 2.2 Brain — agent runtime

The core is a single agent loop driven by a tool-use-capable LLM. Concretely:

- **Model:** Claude Sonnet 4.6 for the default loop. Cheaper Haiku 4.5 for routine classification (categorising a webhook, classifying a spend). Switch to Opus 4.6 for hard reasoning (trading proposals, ambiguous calls).
- **Tool use:** Anthropic's tool-use API. Each tool is a typed function with a JSON schema. The agent picks tools based on observation + intent; the runtime dispatches and feeds the result back.
- **Working memory:** the conversation thread for the current task — observations, tool calls, results — kept in context.
- **Long-term memory:** a vector store (sqlite-vss, Chroma, or LanceDB) of past sessions, decisions, and user preferences. Retrieved via a `recall` tool the agent can call.
- **Policy engine:** a deterministic pre-flight check, NOT an LLM check, that runs before every gated tool call. It enforces hard rules: "never propose a trade above 2% of account equity," "never call a number not in the approved-domain list without confirmation," "never spend if today's total is over €100." If a check fails, the call is rejected before reaching the tool. This is your hardcoded safety net.

The agent loop is deliberately small — perceive → plan → call tool → observe → repeat until the task is resolved or escalation is needed.

### 2.3 Tools — open tier

These the agent calls without asking. The category is "things that observe or draft, but don't reach into the world irreversibly."

| Tool | Purpose | Implementation |
|------|---------|----------------|
| `web_search` | Look things up | Tavily API, Brave Search API, or DuckDuckGo HTML scrape |
| `web_fetch` | Read a specific page | `httpx` + readability parser; render JS pages via Playwright if needed |
| `home_assistant` | Lights, music, climate, sensors | Home Assistant REST API — read state freely, write to non-critical entities (lights, scenes); critical entities (locks, alarm, garage) move to gated |
| `calendar_read` | What's on the schedule | CalDAV / Google Calendar / Microsoft Graph |
| `mail_draft` | Compose, don't send | IMAP read + draft to local store; sending is gated |
| `notes` | Local knowledge base | A markdown vault (Obsidian-compatible) the agent reads/writes |
| `recall` | Long-term memory lookup | Vector search over past sessions |

### 2.4 Tools — gated tier

These all route through the approval surface. The shape of every gated tool is the same: the LLM proposes a structured action; the policy engine validates it; the proposal is shown to you with full context; you approve or reject.

**`payments`.** The agent prepares a Stripe Checkout session OR a charge against a virtual card (see §5 for the spending-limit design). The proposal includes: merchant name, line items, total, the agent's stated reason, and the budget bucket it would draw from. Approval is one tap on your phone.

**`trade`.** The agent proposes an order (instrument, side, size, type, optional stop/take-profit) plus its reasoning and the supporting observations from the perception layer. Phase 1 routes to a paper account on FXOpen (or any broker — Alpaca and Interactive Brokers both have first-class paper APIs). Going live requires a separate explicit unlock per session, with a per-trade confirmation that includes a 5-second cooldown so you can't tap through reflexively.

**`call_phone`.** Outbound voice calls through Twilio Programmable Voice. The agent generates a script + the realtime voice model (ElevenLabs Conversational, OpenAI Realtime, or Deepgram Voice Agent) drives the conversation. The first sentence on every call is a disclosure: *"Hello, this is an AI assistant calling on behalf of [User Name] to [purpose]. Is that alright to proceed?"* The call is recorded (with disclosure to the other party), transcribed, and pushed to the audit log. Calls require approval per call.

**`shell` / `file_write`.** Execute commands or modify files on your machine. Runs inside a sandbox (Docker container, or macOS App Sandbox, or `firejail` on Linux) with an allow-list of commands and a writable scratch directory. Anything outside that — installing packages, modifying system files, touching anything in `~/Documents` — needs approval per action.

**`message_send`.** Email send, SMS, Slack, anything that puts content in front of another human. Always requires approval; the approval shows the rendered message body.

### 2.5 Approval gate

A small service that sits between the agent and gated tools. Implementation: a Python or Node service holding a queue of pending approvals; each approval has a structured payload (the proposed action), a reasoning summary, a budget-impact line, and a TTL. Surfaces:

- **Push** — Pushover, ntfy, or a Twilio SMS for urgency. One-tap deeplink that opens an approval page.
- **In-app** — a simple web UI on `localhost` or a small mobile app via Expo / React Native.
- **Voice** — for low-stakes confirmations the agent can ask aloud and listen for "yes" / "no" via the same voice stack. Never use voice confirmation alone for spend or trades.

Tier rules:

| Stake | Surface | Cooldown |
|-------|---------|----------|
| Information lookup, draft | none | none |
| Smart-home (non-critical) | none, post-hoc notify | none |
| Smart-home (critical: lock, alarm) | one-tap | 0s |
| Spend €0–10 | post-hoc notify only | 0s |
| Spend €10–100 | one-tap | 0s |
| Spend €100+ (if cap is raised) | reasoning + tap | 5s |
| Outbound call | one-tap with script preview | 0s |
| Trade (paper) | none | none |
| Trade (live) | per-trade confirm | 5s |
| Shell command outside sandbox | per-command | 0s |

### 2.6 Security and governance

**Secret vault.** All API keys, card details, account credentials live in a real secret store — Bitwarden CLI, 1Password Connect, HashiCorp Vault, or macOS Keychain via `security` CLI. Never in `.env` files committed anywhere, never plaintext on disk. The agent's tools fetch secrets at call time with scoped, short-TTL tokens.

**Sandboxing.** Tool execution runs in isolated environments. Shell tool: Docker container with no network except to allowed domains, ephemeral filesystem. Web fetch: a separate container with strict egress rules. This limits blast radius if a tool is misused or compromised.

**Audit log.** Every event — observation received, plan generated, tool called, approval requested, approval granted/denied, external response — appended to an immutable log. SQLite with a hash chain (each row's hash includes the previous row's hash) gives tamper-evidence at zero cost. Logs include the LLM's reasoning so you can later ask "why did it propose that?".

**Kill switch.** A single command (`jarvis stop`) or a physical button (a HomeKit/Home Assistant scene tied to a hardware button) that immediately revokes all outstanding approvals and pauses every monitor and tool. Useful when something is going wrong and you don't want to debug — just stop everything.

**Policy as code.** Rules like "no spend on weekends," "no trades during scheduled news events," "no calls between 22:00 and 08:00 unless I'm awake" live in a YAML or DSL file the policy engine reads. Easier to audit than inline conditionals.

---

## 3. Tech stack — concrete choices

| Layer | Choice | Rationale |
|-------|--------|-----------|
| LLM brain | Claude Sonnet 4.6 (default), Haiku 4.5 (classification), Opus 4.6 (hard reasoning) | Tool use is first-class; pricing tiers fit the loop |
| Wake word | openWakeWord | Free, open source, decent accuracy |
| STT | faster-whisper (local) or Deepgram (cloud) | Local is private + free; cloud is lower latency |
| TTS | Piper (local) or ElevenLabs (cloud) | Piper is good enough for ambient feedback; ElevenLabs for phone calls |
| Realtime voice (calls) | ElevenLabs Conversational AI or OpenAI Realtime | Lower latency than STT→LLM→TTS chained |
| Telephony | Twilio Programmable Voice | Mature, EU coverage, recording support |
| Smart home | Home Assistant | Self-hosted, supports almost everything |
| Payments | Stripe Checkout + Revolut/bunq virtual card | Stripe for online merchants, virtual card with hard cap as backstop |
| Trading (paper) | Alpaca paper account or FXOpen demo | Both have first-class APIs; pick whichever matches your real-account broker |
| Vector memory | LanceDB or sqlite-vss | Embedded, no separate service |
| Event bus | Redis Streams or NATS | Both are simple to run locally |
| Approval surface | ntfy.sh + a small FastAPI page | ntfy for push, FastAPI for the approval UI |
| Secret vault | 1Password Connect or Bitwarden CLI | Easier than rolling your own, both have programmatic access |
| Sandbox | Docker (Linux) or macOS App Sandbox | Standard, well-understood isolation |
| Runtime | Python 3.12 + asyncio | Most LLM/voice libs are Python-first |
| Audit log | SQLite with hash chain | Zero-ops, tamper-evident |

---

## 4. Worked example — observation to execution

A complex request, end-to-end, showing how the modules cooperate.

**Scenario.** You say: *"Jarvis, book a table for two at Lupa for Saturday at 7pm. Pay any deposit they need. Tell me when it's done."*

**Step 1 — Perception.** Wake-word fires. Whisper transcribes. The transcript and metadata (timestamp, source = voice) hit the event bus.

**Step 2 — Intent and plan.** The brain receives the transcript. It identifies a multi-tool task: lookup → call → maybe pay → notify. It writes a plan to working memory:
1. Find Lupa's phone number and current opening hours.
2. Place a call, request the booking.
3. If a deposit is needed, request approval.
4. Notify on completion.

**Step 3 — Open tool: web search.** Agent calls `web_search("Lupa restaurant phone number Amsterdam")` (assuming city from your profile). It calls `web_fetch` on the top result to confirm the number and check that the restaurant takes phone bookings (vs only OpenTable).

**Step 4 — Policy pre-flight.** Before the gated `call_phone`, the policy engine checks: number is in EU, not on a blocklist, time is within the agent's allowed calling window (08:00–21:00 by default), no other call in progress.

**Step 5 — Approval request.** A push notification arrives on your phone:

> *Outbound call: Lupa, +31 20 555 0182*  
> *Purpose: book table for 2, Saturday 19:00*  
> *Script preview: "Hello, this is an AI assistant calling on behalf of Nickos to book a table for two on Saturday at 7pm…"*  
> *[Approve] [Reject] [Edit]*

You tap Approve.

**Step 6 — Gated tool: phone call.** Twilio dials. The realtime voice model handles the conversation:

> *Agent:* "Hello, this is an AI assistant calling on behalf of Nickos to book a table for two this Saturday at 7pm. Is that alright to proceed?"  
> *Restaurant:* "Yes, what name?"  
> *Agent:* "Nickos. The phone number for the booking is [your number]."  
> *Restaurant:* "We'll need a €20 deposit per person. Can you pay now over the phone?"

The realtime model recognises this as a payment request mid-call. It does NOT take the deposit on the call (no card data ever read aloud, both for security and PCI reasons). Instead:

> *Agent:* "I'll send the deposit by a different method shortly. Can you hold the booking for the next 15 minutes while I arrange that?"  
> *Restaurant:* "Sure, I'll hold it under Nickos."

Call ends. Transcript written to audit log.

**Step 7 — Payment proposal.** Agent now needs to send €40. It searches for "Lupa" in your saved-merchants list (none). It calls `web_search` for the restaurant's payment options, finds they have a Tikkie / iDEAL link on their site. It prepares a payment proposal:

> *Payment: Lupa, €40.00*  
> *Method: Stripe Checkout to merchant URL [restaurant's deposit page]*  
> *Reason: Saturday 19:00 booking deposit (2 × €20)*  
> *Budget impact: €40 of €100 monthly cap remaining → €60 after*  
> *[Approve] [Reject]*

**Step 8 — Policy pre-flight.** Hard cap check: €40 ≤ €100 cap remaining. Merchant URL passes domain check. Tier rule: €10–100 → one-tap, no cooldown.

**Step 9 — Approval and charge.** You approve. The agent uses the virtual card (held in the vault) to complete the Stripe Checkout session. Webhook fires back from Stripe / Revolut confirming the charge. Audit log updated.

**Step 10 — Notify.** Agent speaks aloud (or messages you): *"Booked Lupa for Saturday 7pm under your name, €40 deposit paid. €60 remaining on this month's cap."*

Total elapsed time: 2–4 minutes, two taps from you. The agent did the lookup, the call, the payment routing, and the bookkeeping; you stayed in the loop on every step that touched money or a stranger.

---

## 5. Spending controls in detail

Recapping the design we landed on, fleshed out.

**Hard cap at the card.** Issue a virtual card dedicated to the agent through Revolut, bunq, Wise, or Stripe Issuing. Configure: monthly limit €100 (matches your stated cap), transaction limit €50 (so a single buggy charge can't burn the whole budget), merchant categories restricted to what you'd actually want the agent to spend on (food delivery, transport, online retail — exclude gambling, cash advances, crypto). Mastercard or Visa enforces all of this; the card declines anything outside the rules regardless of what the agent tries.

**Soft layer in the agent.** The agent maintains a budget ledger in SQLite:

```
table budget:
  category text,        -- "food", "transport", "subscriptions", …
  monthly_cap_eur int,
  spent_this_month_eur int,
  cooldown_until timestamp
```

Before any payment proposal, the agent classifies the spend and checks the per-category cap. It refuses to propose anything that would exceed it. This is the day-to-day budgeting tool — easier than waiting for the card to decline mid-checkout.

**Tiered approval by amount** (already in the gate table above).

**Reconciliation webhook.** Revolut and Stripe both push webhooks on each transaction. The webhook handler updates the agent's ledger so the soft layer matches reality — and crucially, it surfaces *unexpected* charges (charge cleared but no agent proposal exists) as an immediate alert to you. That's how you catch a stolen card or a duplicate charge fast.

**Cooldowns and rate limits.** The policy engine enforces "no more than 3 transactions per hour" and "no transaction within 60s of the previous one." Catches runaway loops if the agent gets stuck retrying.

**Kill switch.** `jarvis stop` revokes the virtual card token from the vault. The card is now unusable until you re-grant. Pair with a Home Assistant scene tied to a physical button for in-the-moment use.

---

## 6. Trading — the modified design

Phase 1 is paper trading with full agent autonomy. Phase 2 is live with per-trade confirmation. There is no "phase 3 = unattended live trading" in this design, by intent.

**Paper phase mechanics.** Connect to FXOpen's demo account or Alpaca paper API. The agent can monitor markets (read-only data from the broker), generate signals, propose trades, execute them on the paper account, and write outcomes to the audit log. You review weekly. Treat the paper period as the calibration window — log every proposal, even rejected ones, so you can build a track record before any real money.

**Live phase mechanics.** When you're satisfied with paper performance, enable live with three constraints baked in:

1. *Per-trade confirmation gate.* Every order requires your tap, with a 5-second forced cooldown. The proposal shows: instrument, side, size as % of account equity, the agent's reasoning, a link to the supporting observations, the stop/take-profit, and the worst-case loss in EUR.
2. *Hard position-size limit.* Policy engine refuses proposals over 2% of account equity, regardless of agent reasoning. This is a deterministic check, not an LLM check.
3. *Daily kill switch.* If the account drops more than X% in a day, all live trading auto-pauses for 24 hours. The agent can still propose, but the gate refuses to execute.

**What I won't design.** A live-trading mode with no per-trade confirmation. The combination of LLM hallucination + market commentary as adversarial input + irreversible financial action has a worse expected-value profile than not running it at all. If you decide later you want fully autonomous live trading, that's a different project with very different review requirements.

---

## 7. Outbound calling — disclosure design

The disclosure is non-negotiable in the script for legal reasons, but it also pays for itself in success rate. The opening template:

> *"Hello, this is an AI assistant calling on behalf of [User Name] to [purpose]. Is that alright to proceed?"*

Three reasons the disclosure works in practice:

1. *Legal.* California SB 1001 (since 2019), the EU AI Act (Article 50, in force from 2026), and a growing list of US states require AI to identify itself when interacting with consumers. Twilio's terms also require disclosure for AI-driven calls.
2. *Trust.* People are far more cooperative when they aren't trying to figure out if they're being scammed. Hidden AI calls are the scam-call playbook; opting out of that pattern explicitly is a feature.
3. *Recovery.* Honest disclosure means you can record (with consent at the start of the call), which means you have a transcript when something goes wrong with the booking later.

The agent should also handle "no, I'd rather speak to a human" gracefully — the script has a branch that says "Understood — I'll have Nickos call you back during business hours" and ends the call.

---

## 8. Phased rollout

Six phases, each independently useful. Don't build it all before using any of it.

**Phase 1 — Brain + open tools (1–2 weeks).** Just the agent runtime, web search, web fetch, calendar read, notes. Chat-only interface. Goal: prove the planning loop works on real tasks, build the audit log infrastructure.

**Phase 2 — Voice (1 week).** Add wake word, STT, TTS. Same open tools. Now it's a voice-first assistant. Use it daily to surface bugs.

**Phase 3 — Smart home (1 week).** Home Assistant integration. Read all entities, write to non-critical ones. Useful, low-risk, builds confidence in the policy engine.

**Phase 4 — Approval surface + first gated tool (2 weeks).** Build the approval gate, push notifications, the in-app approval UI. Wire `mail_send` as the first gated tool — high-frequency, low-stakes, gives you fast iteration on the approval UX.

**Phase 5 — Payments (2 weeks).** Set up the virtual card with €100 cap. Build the budget ledger. Wire Stripe Checkout. Test on small purchases first (€2 coffee subscriptions, €5 e-books). Watch the reconciliation webhook closely.

**Phase 6 — Telephony + paper trading (2–4 weeks).** Twilio integration with the disclosure script. Paper trading account with full autonomy. These are the most complex — leave for last.

**Phase 7 (gated by your judgment) — live trading.** Only after paper has shown a real edge over a meaningful sample. Even then, per-trade confirmation, position-size cap, daily drawdown kill switch.

---

## 9. Open questions before scaffolding

Things to decide before I write code:

1. **Hosting.** Run on your laptop, a home server (Raspberry Pi 5 / NUC), or a cheap VPS? Affects sandboxing options and 24/7 monitoring.
2. **Voice latency tolerance.** Local Whisper + Piper has ~1–2s latency. Cloud (Deepgram + ElevenLabs) is sub-500ms. The first is private and free; the second feels noticeably more like Jarvis. Pick one to start.
3. **Mobile approval surface.** Are you comfortable with ntfy.sh (free, open, third-party server) or do you want to self-host the push channel? Or build a thin native app?
4. **Broker for paper trading.** FXOpen demo, Alpaca, IBKR — which matches what you'd eventually go live on?
5. **Smart home — which "critical" entities exist?** Locks, alarm, garage, oven? These need to be in the gated list explicitly.
6. **Disclosure language for calls.** Do you want a fixed script or per-call customisation? Some users prefer "AI assistant," others "automated assistant," others "assistant" — small wording differences change call success.

Answers to these shape the scaffold meaningfully. Worth ten minutes before code.

---

*This design intentionally trades some autonomy for safety — particularly around payments and trading. The result is an agent that's still doing 95% of the work for you while keeping you in the loop on the 5% that, if it went wrong, would actually hurt.*
