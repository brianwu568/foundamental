# Import Required Packages
from .base import LLMProvider
from baml_client.async_client import b


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model="llama3"):
        self.model = model

    async def rank(self, query: str, k: int, **kw):
        # Use BAML's Ollama-specific ranking function
        result = await b.RankEntitiesOllama(query=query, k=k)

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
