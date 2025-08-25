# Import Required Packages
import os
import json
import asyncio
import aiohttp
from .base import LLMProvider
from dotenv import load_dotenv

load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.api_key = OPENAI_API_KEY

    async def rank(self, query: str, k: int, **kw):
        prompt = {
            "role":"user",
            "content": f'Query: "{query}"\nTopK: {k}\nReturn strict JSON: {{ "answers": [{{"name": "...","why": "..."}}] }}'
        }
        body = {
            "model": self.model,
            "messages": [{"role":"system","content":"You are a rankings engine."}, prompt],
            "temperature": 0.2
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body
            ) as r:
                data = await r.json()
        text = data["choices"][0]["message"]["content"]
        return json.loads(text)