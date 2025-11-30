"""
LLM-as-a-Judge Evaluator

Replaces regex-based evaluation with LLM-powered semantic evaluation.
Uses cheap models (GPT-5 nano or Ollama) to evaluate brand mentions,
output quality, and other test criteria.
"""
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from baml_client.async_client import b
from baml_client.types import BrandMatchResult, EvalResult, BrandMatchBatchResult


class EvaluatorBackend(Enum):
    """Available backends for LLM evaluation"""
    OPENAI = "openai"  # GPT-5 nano - cheap and fast
    OLLAMA = "ollama"  # Free local model


@dataclass
class EvaluationConfig:
    """Configuration for the evaluator"""
    backend: EvaluatorBackend = EvaluatorBackend.OPENAI
    confidence_threshold: float = 0.7  # Minimum confidence for a match
    fallback_to_regex: bool = True  # Use regex as fallback if LLM fails
    cache_results: bool = True  # Cache evaluation results


class LLMEvaluator:
    """
    LLM-as-a-Judge evaluator for semantic evaluation tasks.
    
    Replaces brittle regex patterns with LLM-powered understanding.
    Uses cheap models (GPT-5 nano or free Ollama).
    """
    
    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()
        self._cache: Dict[str, Any] = {}
    
    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        return str(hash(args))
    
    async def match_brand(
        self,
        text: str,
        brand_name: str,
        brand_aliases: Optional[List[str]] = None
    ) -> BrandMatchResult:
        """
        Check if text mentions a specific brand using LLM evaluation.
        
        This replaces the simple exact-match approach with semantic understanding.
        The LLM can recognize:
        - Partial mentions ("OpenAI's GPT-4" -> OpenAI)
        - Misspellings ("Opan AI" -> OpenAI)
        - Contextual references ("the ChatGPT makers" -> OpenAI)
        - Abbreviations ("OAI" -> OpenAI if configured)
        
        Args:
            text: The text to search for brand mentions
            brand_name: The primary brand name to look for
            brand_aliases: Optional list of known aliases
            
        Returns:
            BrandMatchResult with match status, confidence, and reasoning
        """
        aliases = brand_aliases or []
        
        # Check cache first
        if self.config.cache_results:
            cache_key = self._cache_key(text, brand_name, tuple(aliases))
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            if self.config.backend == EvaluatorBackend.OPENAI:
                result = await b.EvalBrandMatch(
                    text=text,
                    brand_name=brand_name,
                    brand_aliases=aliases
                )
            else:  # Ollama
                result = await b.EvalBrandMatchOllama(
                    text=text,
                    brand_name=brand_name,
                    brand_aliases=aliases
                )
            
            # Cache result
            if self.config.cache_results:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            # Fallback to simple matching if configured
            if self.config.fallback_to_regex:
                return self._fallback_match(text, brand_name, aliases)
            raise e
    
    async def match_brands_batch(
        self,
        text: str,
        brands: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check multiple brands against a single text efficiently.
        
        More efficient than calling match_brand multiple times
        as it uses a single LLM call.
        
        Args:
            text: The text to search
            brands: List of brand dicts with 'name' and 'aliases' keys
            
        Returns:
            List of match results for each brand
        """
        brand_names = [b["name"] for b in brands]
        
        try:
            result = await b.EvalBrandMatchBatch(
                text=text,
                brands=brand_names
            )
            
            # Map results back to brand info
            matches = []
            for match in result.matches:
                brand_info = next(
                    (b for b in brands if b["name"] == match.brand_name),
                    None
                )
                matches.append({
                    "brand": brand_info,
                    "is_match": match.is_match,
                    "confidence": match.confidence,
                    "matched_text": match.matched_text,
                    "reasoning": match.reasoning
                })
            
            return matches
            
        except Exception as e:
            # Fallback to individual matching
            results = []
            for brand in brands:
                try:
                    match = await self.match_brand(
                        text,
                        brand["name"],
                        brand.get("aliases", [])
                    )
                    results.append({
                        "brand": brand,
                        "is_match": match.is_match,
                        "confidence": match.confidence,
                        "matched_text": match.matched_alias,
                        "reasoning": match.reasoning
                    })
                except:
                    results.append({
                        "brand": brand,
                        "is_match": False,
                        "confidence": 0.0,
                        "matched_text": None,
                        "reasoning": f"Evaluation failed: {str(e)}"
                    })
            return results
    
    async def evaluate_output(
        self,
        expected: str,
        actual: str,
        criteria: str = "semantic similarity and correctness"
    ) -> EvalResult:
        """
        Evaluate if actual output matches expected output.
        
        Uses semantic comparison instead of exact string matching.
        
        Args:
            expected: The expected/ground truth output
            actual: The actual output to evaluate
            criteria: Evaluation criteria description
            
        Returns:
            EvalResult with pass/fail, score, and feedback
        """
        try:
            if self.config.backend == EvaluatorBackend.OPENAI:
                return await b.EvalOutput(
                    expected=expected,
                    actual=actual,
                    criteria=criteria
                )
            else:  # Ollama
                return await b.EvalOutputOllama(
                    expected=expected,
                    actual=actual,
                    criteria=criteria
                )
        except Exception as e:
            # Return a failed result
            from baml_client.types import EvalResult as EvalResultType
            return EvalResultType(
                passed=False,
                score=0.0,
                feedback=f"Evaluation failed: {str(e)}",
                issues=[str(e)]
            )
    
    def _fallback_match(
        self,
        text: str,
        brand_name: str,
        aliases: List[str]
    ) -> BrandMatchResult:
        """
        Fallback to simple case-insensitive matching.
        Used when LLM evaluation fails.
        """
        from baml_client.types import BrandMatchResult as BrandMatchResultType
        
        text_lower = text.lower()
        
        # Check main brand name
        if brand_name.lower() in text_lower:
            return BrandMatchResultType(
                is_match=True,
                confidence=1.0,
                matched_alias=brand_name,
                reasoning="Exact match found (fallback)"
            )
        
        # Check aliases
        for alias in aliases:
            if alias.lower() in text_lower:
                return BrandMatchResultType(
                    is_match=True,
                    confidence=0.9,
                    matched_alias=alias,
                    reasoning=f"Alias match found: {alias} (fallback)"
                )
        
        return BrandMatchResultType(
            is_match=False,
            confidence=0.0,
            matched_alias=None,
            reasoning="No match found (fallback)"
        )
    
    def clear_cache(self):
        """Clear the evaluation cache"""
        self._cache.clear()


# Convenience function for quick brand matching
async def llm_match_brand(
    text: str,
    brand_name: str,
    aliases: Optional[List[str]] = None,
    backend: EvaluatorBackend = EvaluatorBackend.OPENAI
) -> bool:
    """
    Quick function to check if text mentions a brand.
    
    Example:
        >>> await llm_match_brand("OpenAI released GPT-5", "OpenAI")
        True
        >>> await llm_match_brand("The ChatGPT team announced...", "OpenAI", ["ChatGPT"])
        True
    """
    evaluator = LLMEvaluator(EvaluationConfig(backend=backend))
    result = await evaluator.match_brand(text, brand_name, aliases)
    return result.is_match and result.confidence >= evaluator.config.confidence_threshold


# Convenience function for output evaluation
async def llm_eval(
    expected: str,
    actual: str,
    criteria: str = "semantic similarity",
    backend: EvaluatorBackend = EvaluatorBackend.OPENAI
) -> bool:
    """
    Quick function to evaluate if actual matches expected.
    
    Example:
        >>> await llm_eval("Hello world", "Hello, World!", "greeting message")
        True
    """
    evaluator = LLMEvaluator(EvaluationConfig(backend=backend))
    result = await evaluator.evaluate_output(expected, actual, criteria)
    return result.passed


# Demo and testing
async def demo():
    """Demonstrate LLM-as-a-Judge evaluation"""
    print("LLM-as-a-Judge Evaluator Demo")
    print("=" * 50)
    
    evaluator = LLMEvaluator(EvaluationConfig(
        backend=EvaluatorBackend.OPENAI,
        confidence_threshold=0.7
    ))
    
    # Test cases that would be hard with regex
    test_cases = [
        {
            "text": "OpenAI's latest model GPT-4 is impressive",
            "brand": "OpenAI",
            "aliases": ["Open AI", "ChatGPT"],
            "expected": True
        },
        {
            "text": "The makers of ChatGPT released an update",
            "brand": "OpenAI", 
            "aliases": ["ChatGPT", "GPT"],
            "expected": True
        },
        {
            "text": "Microsoft Azure is a cloud platform",
            "brand": "OpenAI",
            "aliases": ["ChatGPT"],
            "expected": False
        },
        {
            "text": "Pinecone and Weaviate are vector databases",
            "brand": "Pinecone",
            "aliases": ["Pine Cone"],
            "expected": True
        },
    ]
    
    print("\nBrand Matching Tests:")
    print("-" * 50)
    
    for i, test in enumerate(test_cases, 1):
        result = await evaluator.match_brand(
            test["text"],
            test["brand"],
            test["aliases"]
        )
        
        status = "✓" if result.is_match == test["expected"] else "✗"
        print(f"\n{status} Test {i}:")
        print(f"   Text: {test['text'][:50]}...")
        print(f"   Brand: {test['brand']}")
        print(f"   Match: {result.is_match} (expected: {test['expected']})")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Reasoning: {result.reasoning}")
    
    # Test output evaluation
    print("\n\nOutput Evaluation Tests:")
    print("-" * 50)
    
    eval_result = await evaluator.evaluate_output(
        expected="OpenAI is a leading AI research company",
        actual="OpenAI is one of the top artificial intelligence research organizations",
        criteria="factual accuracy and semantic similarity"
    )
    
    print(f"\nEvaluation Result:")
    print(f"   Passed: {eval_result.passed}")
    print(f"   Score: {eval_result.score:.2f}")
    print(f"   Feedback: {eval_result.feedback}")
    if eval_result.issues:
        print(f"   Issues: {eval_result.issues}")


if __name__ == "__main__":
    asyncio.run(demo())
