# Import Required Packages
import os
from .base import LLMProvider
from baml_client.async_client import b
from dotenv import load_dotenv

load_dotenv()


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model="gpt-4o-mini"):
        self.model = model

        # Ensure API key is available
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables.")

    async def rank(self, query: str, k: int, **kw):
        # Use BAML's OpenAI-specific ranking function
        result = await b.RankEntitiesOpenAI(query=query, k=k)

        # Convert BAML RankingResult to the expected format
        return {
            "answers": [
                {
                    "name": answer.name,
                    "why": answer.why
                }
                for answer in result.answers
            ]
        }
