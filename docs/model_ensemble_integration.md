# Jarvis Model Selection & Ensemble Integration

## Overview
Jarvis supports multiple LLMs (e.g., Claude, Ollama) and uses an adapter pattern to allow flexible model selection, fallback, and ensemble strategies. This document explains how the system works and how to extend it.

---

## Key Concepts

### 1. Model Adapters
- Each LLM (Claude, Ollama, etc.) is wrapped in an adapter class (see `jarvis/ollama_adapter.py`).
- Adapters provide a unified interface for generating completions, regardless of backend.

### 2. Model Selection
- The active model is set in the config (`Config.model`).
- Jarvis selects the model based on config, availability, and rate limits.
- Fallback logic is implemented: if the primary model is unavailable (e.g., Claude rate-limited), Jarvis falls back to a local model (Ollama).

### 3. Ensemble/Fallback Logic
- Ensemble logic can be extended to query multiple models and combine results.
- Fallback is automatic if a model fails or is rate-limited.

---

## How It Works
- The backend (`brain.py`, `ollama_adapter.py`, etc.) checks the config and available adapters.
- When a request is made, the system tries the primary model first.
- If the primary fails, it falls back to the next available adapter.
- Adapters for voice (wake word, STT, TTS) and chat use the same pattern.

---

## Adding a New Model Adapter
1. Create a new adapter class (see `ollama_adapter.py` as a template).
2. Implement a `generate()` method matching the interface.
3. Register the adapter in the backend logic (e.g., in `brain.py`).
4. Update config to allow selection of the new model.

---

## Configuration
- Set the default model in environment or config file (e.g., `ANTHROPIC_MODEL`, `OLLAMA_MODEL`).
- Fallback/ensemble order is determined by backend logic and can be extended.

---

## Example: Ollama Adapter
```
from jarvis.ollama_adapter import OllamaLLMAdapter
ollama = OllamaLLMAdapter(model="llama3")
response = ollama.generate("Hello, world!")
```

---

## Extending Ensemble Logic
- To combine outputs from multiple models, implement aggregation logic in the backend (e.g., majority vote, confidence weighting).
- Update the backend to call multiple adapters and merge results as needed.

---

## References
- `jarvis/ollama_adapter.py`
- `jarvis/brain.py`
- `jarvis/config.py`
- `jarvis/perception/voice/` (for voice adapters)
- `jarvis/perception/chat/` (for chat adapters)

---

For further help, see the code comments in the referenced files or ask for implementation examples.
