"""
Ollama LLM Adapter for Jarvis

Provides a unified interface to query local Ollama models via HTTP API.
"""
import requests

class OllamaLLMAdapter:
    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt, system=None, stream=False, **kwargs):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        payload.update(kwargs)
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["response"] if "response" in data else data

# Example usage:
# ollama = OllamaLLMAdapter(model="dolphin-mistral")
# print(ollama.generate("Why is the sky blue?"))
