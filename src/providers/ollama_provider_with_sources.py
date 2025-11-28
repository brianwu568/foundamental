# Import Required Packages
from .base import LLMProvider
from baml_client.async_client import b


class OllamaProviderWithSources(LLMProvider):
    """Ollama provider that requests sources and confidence scores"""
    name = "ollama"

    def __init__(self, model="llama3"):
        self.model = model

    async def rank(self, query: str, k: int, **kw):
        # Use BAML's Ollama-specific ranking function with sources
        result = await b.RankEntitiesWithSourcesOllama(query=query, k=k)

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
