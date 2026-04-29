# Jarvis Voice Agents Task List

## Completed ✅

- [x] ElevenLabs TTS API integration (/hud/tts endpoint)
- [x] Web Audio API MP3 playback
- [x] Voice latency optimization (stability 0.5, streaming_latency 4)
- [x] Jarvis male voice configuration (Eric - cjVigY5qzO86Huf0OWal)
- [x] EVA female voice configuration (The Asians - HWkBpcT0RMFmyNMInxtE)
- [x] Agent switching system (dropdown UI + voice commands)
- [x] Status badge dynamic display (emoji + label)
- [x] Agent persistence via localStorage
- [x] Dynamic wake phrase detection (agent-specific)
- [x] Network access from MacBook (0.0.0.0 binding)
- [x] Mobile font scaling for phone usability
- [x] Firewall security (home network only)

## In Progress 🟡

- [ ] Test EVA wake phrases ("hey eva", "eva wake up", etc.)
- [ ] Verify agent-specific voice selection on voice commands
- [ ] Test full end-to-end: switch agent → say wake phrase → listen

## Backlog 📋

### Voice & Audio
- [ ] Per-agent voice preference persistence
- [ ] Custom voice profiles (user-recorded voice cloning)
- [ ] Voice modulation (pitch, speed adjustments)
- [ ] Ambient noise filtering before speech recognition
- [ ] Audio level detection (visual feedback)
- [ ] Fallback TTS if ElevenLabs API fails

### Agent Personality
- [ ] Separate system prompts per agent (Jarvis vs EVA)
- [ ] Agent-specific response templates
- [ ] Behavioral directives per agent
- [ ] Emotional tone configuration (professional, casual, formal)
- [ ] Context awareness (remember previous agent selections)

### Chat & UI
- [ ] Per-agent chat history (separate conversation logs)
- [ ] Agent switcher in mobile view optimization
- [ ] Notification sounds per agent
- [ ] Quick-access agent buttons in top bar
- [ ] Agent availability status indicator

### Integration
- [ ] Backend API route for /hud/ask to respect current agent
- [ ] Agent context passed to LLM for personalized responses
- [ ] Multi-agent collaboration (Jarvis + EVA working together)
- [ ] Agent-specific API keys/auth if needed

### Testing & Deployment
- [ ] Unit tests for agent switching logic
- [ ] E2E tests for wake phrase detection
- [ ] Voice quality testing across network
- [ ] Load testing (multiple agents + concurrent requests)
- [ ] Documentation for agent customization

### Security & Performance
- [ ] HTTPS/SSL for remote access (if exposing beyond home network)
- [ ] Rate limiting on TTS synthesis
- [ ] Cache common responses per agent
- [ ] Agent authentication (if multi-user)
- [ ] Audit logging for agent interactions

---

## Notes

**Voice IDs Reference:**
- Jarvis (Male): Eric (`cjVigY5qzO86Huf0OWal`)
- EVA (Female): The Asians (`HWkBpcT0RMFmyNMInxtE`)

**Wake Phrases:**
- Jarvis: "hey jarvis", "jarvis wake up", "wake up jarvis", "ok jarvis"
- EVA: "hey eva", "eva wake up", "wake up eva", "ok eva"

**Network:**
- Server: `0.0.0.0:8080` (all interfaces)
- Home Access: `http://192.168.0.171:8080/hud/cc`
- MacBook Access: Same URL from home WiFi
- Security: Firewall restricted to 192.168.0.0/24

**Key Files:**
- Frontend: `jarvis/web/command_center/app.js` (agent switching, wake phrases)
- Config: `jarvis/config.py` (voice IDs, TTS settings)
- Backend: `jarvis/approval_api.py` (/hud/tts endpoint)
- Startup: `jarvis/__main__.py` (_approvals_api function)
