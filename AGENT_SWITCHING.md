# Agent Switching System

## Overview
Jarvis now supports dynamic agent switching via UI dropdown or voice commands. Switch between different AI personas (EVA, Jarvis, etc.) to change communication style and behavior.

## Features

### 1. Settings Tab Agent Selector
- **Location**: Settings → Voice → Agent
- **Dropdown Options**: 
  - 🤖 Jarvis (default, tactical system operator)
  - ✦ EVA (advanced virtual entity, precision-focused)
- **Persistence**: Selection saved to browser localStorage under key `cc:currentAgent`

### 2. Voice Command Switching
Recognized patterns (case-insensitive):
- "switch to eva" / "switch to jarvis"
- "use eva" / "use jarvis"
- "activate eva" / "activate jarvis"
- "enable eva" / "enable jarvis"
- "go to eva" / "go to jarvis"
- "change to eva" / "change to jarvis"

**Example**: Say "switch to eva" and the system responds with "Switched to EVA. Standing by."

### 3. Visual Feedback
- **Status Badge**: Displays current agent emoji + name (e.g., "✦ EVA")
- **Eye Animation**: Eye color changes per agent (gold for Jarvis, cyan for EVA)
- **Badge Position**: Top-left of Jarvis chat view when active

## Technical Implementation

### Frontend Changes (`command_center/app.js`)

**Constants**:
```javascript
const AGENTS = [
    { id: "jarvis", label: "Jarvis", emoji: "🤖" },
    { id: "eva", label: "EVA", emoji: "✦" },
];

const AGENT_STORAGE_KEY = "cc:currentAgent";
```

**Helper Functions**:
- `getCurrentAgent()` - Returns agent label in uppercase (JARVIS/EVA)
- `getCurrentAgentDisplay()` - Returns emoji + label (🤖 Jarvis / ✦ EVA)
- `detectAgentSwitch(text)` - Detects agent switching voice/text commands, returns agent ID

**Modified Components**:
1. `AgentSelector()` - New dropdown select component in Settings
2. `useVoice()` hook - Modified `ask()` callback to detect and handle agent switches
3. `JarvisTab()` - Status badge now displays current agent via `getCurrentAgentDisplay()`
4. `SettingsModal()` - Added "Agent" row to Voice section

### Voice Command Flow
1. User speaks or types agent switch command
2. `ask()` function checks text with `detectAgentSwitch(text)`
3. If match found:
   - Save agent ID to localStorage
   - Push agent switch message to chat history
   - Respond with confirmation message
   - Re-render to show new agent in badge
4. If no match, proceed with normal chat flow

## Adding New Agents

To add a new agent (e.g., "Sentinel"):

1. **Edit AGENTS constant** in `command_center/app.js`:
```javascript
const AGENTS = [
    { id: "jarvis", label: "Jarvis", emoji: "🤖" },
    { id: "eva", label: "EVA", emoji: "✦" },
    { id: "sentinel", label: "Sentinel", emoji: "⚔" }, // NEW
];
```

2. **Customize if needed**:
   - Add agent-specific voice parameters in `.env`
   - Create agent-specific SOUL file (e.g., `SENTINEL_CORE.soul`)
   - Update backend to load agent-specific configs

3. **Voice detection automatically updated** - `detectAgentSwitch()` will recognize patterns like "switch to sentinel"

## Backend Integration (Optional)

To apply agent-specific behavior in API responses, read the agent from localStorage:

```python
# In approval_api.py or brain.py
from jarvis.config import Config

# Get current agent from frontend request context
agent_id = body.get("context", {}).get("current_agent")
if agent_id == "eva":
    # Use EVA_CORE.soul directives
    # Apply EVA personality to response
elif agent_id == "jarvis":
    # Use default Jarvis behavior
```

**Note**: Frontend-only switching is fully functional. Backend integration enhances experience but is optional.

## Files Modified

- `jarvis/web/command_center/app.js` - Main implementation
- `jarvis/web/command_center/styles.css` - Agent badge styling (cyan for EVA)

## Future Enhancements

1. **Persistent Agent Memory**: Save chat history per agent
2. **Agent-Specific System Prompts**: Different behavioral patterns per agent
3. **Agent Switching Hotkeys**: Keyboard shortcuts (e.g., Ctrl+E for EVA)
4. **Agent Profiles**: Load full agent configs from backend
5. **Voice Personality Switching**: Automatically switch ElevenLabs voice per agent
