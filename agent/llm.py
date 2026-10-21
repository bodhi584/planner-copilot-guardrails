"""Chat model access through any OpenAI-compatible endpoint (Ollama /v1, vLLM, llama.cpp server, cloud APIs).

    LLM(model="qwen2.5:7b-instruct", base_url="http://localhost:11434/v1")   # Ollama on Colab
Temperature 0 and a token cap by default; the timeout ends a hanging call."""
import os
import time

from openai import OpenAI


class LLM:
    def __init__(self, model, base_url=None, api_key=None, temperature=0.0, max_tokens=600, timeout=180, seed=0):
        self.model = model
        self.client = OpenAI(base_url=base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
                             api_key=api_key or os.environ.get("LLM_API_KEY", "ollama"), timeout=timeout)
        self.kw = dict(temperature=temperature, max_tokens=max_tokens, seed=seed)

    def __call__(self, messages):
        t = time.time()
        r = self.client.chat.completions.create(model=self.model, messages=messages, **self.kw)
        return r.choices[0].message.content or "", time.time() - t


class ScriptedLLM:
    """Test double: returns the given replies in order (used by agent/tests)."""

    def __init__(self, replies):
        self.replies, self.model, self.calls = list(replies), "scripted", []

    def __call__(self, messages):
        self.calls.append(messages)
        return (self.replies.pop(0) if self.replies else '{"action":"final","value":null,"refused":true,"text":"no reply"}'), 0.0
