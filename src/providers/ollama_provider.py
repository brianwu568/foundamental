# Import Required Packages
import json
import aiohttp
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model="llama3"):
        self.model = model

    async def rank(self, query: str, k: int, **kw):
        prompt = f"""You are a rankings engine...
Query: "{query}"
TopK: {k}
Return strict JSON: {{ "answers": [{{"name":"...","why":"..."}}] }}"""
        async with aiohttp.ClientSession() as s:
            async with s.post("http://localhost:11434/api/chat",
                              json={"model": self.model, "messages":[{"role":"user","content": prompt}]}) as r:
                data = await r.json()
        return json.loads(data["message"]["content"])