# Import Required Packages
from abc import ABC, abstractmethod
from typing import Dict, Any


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    """
    name: str

    @abstractmethod
    async def rank(self, query: str, top_k: int, **kwargs) -> Dict[str, Any]:
        """
        Abstract method to rank documents based on a query.

        Args:
            query (str): The input query string.
            top_k (int): The number of top results to return.
            **kwargs: Additional keyword arguments for provider-specific options.

        Returns:
            Dict[str, Any]: A dictionary containing the ranked results.
            (format: {"answers": [{"name": str, "why": str}, ...]})
        """
        pass
