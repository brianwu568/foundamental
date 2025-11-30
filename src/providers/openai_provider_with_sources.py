# Import Required Packages
import os
from .base import LLMProvider
from baml_client.async_client import b
from dotenv import load_dotenv

load_dotenv()


class OpenAIProviderWithSources(LLMProvider):
    """OpenAI provider that requests sources and confidence scores"""
    name = "openai"

    def __init__(self, model="gpt-5-nano-2025-08-07"):
        self.model = model

        # Ensure API key is available
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables.")

    async def rank(self, query: str, k: int, **kw):
        # Use BAML's OpenAI-specific ranking function with sources
        result = await b.RankEntitiesWithSourcesOpenAI(query=query, k=k)

        # Convert BAML RankingResultWithSources to the expected format
        return {
            "answers": [
                {
                    "name": answer.name,
                    "why": answer.why,
                    "sources": [
                        {
                            "url": source.url,
                            "title": source.title,
                            "description": source.description
                        }
                        for source in answer.sources
                    ],
                    "confidence": answer.confidence
                }
                for answer in result.answers
            ]
        }
