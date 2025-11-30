#!/usr/bin/env python3
"""
LLM-as-a-Judge Evaluation Tests

Tests the LLM evaluator against various edge cases that regex cannot handle.
Uses cheap models (GPT-4o-mini ~$0.15/1M tokens or free Ollama).
"""
import asyncio
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()


async def test_brand_matching():
    """Test brand matching with various edge cases"""
    from llm_evaluator import LLMEvaluator, EvaluationConfig, EvaluatorBackend
    
    print("=" * 60)
    print("LLM-as-a-Judge Brand Matching Tests")
    print("=" * 60)
    
    evaluator = LLMEvaluator(EvaluationConfig(
        backend=EvaluatorBackend.OPENAI,
        confidence_threshold=0.7,
        fallback_to_regex=True,
        cache_results=True
    ))
    
    # Test cases organized by category
    test_cases = [
        # Exact matches - should always pass
        {
            "category": "Exact Match",
            "text": "OpenAI",
            "brand": "OpenAI",
            "aliases": [],
            "expected": True
        },
        {
            "category": "Exact Match",
            "text": "Pinecone",
            "brand": "Pinecone",
            "aliases": [],
            "expected": True
        },
        
        # Partial/contextual matches - regex would fail
        {
            "category": "Partial Match",
            "text": "OpenAI's GPT-4 model is revolutionary",
            "brand": "OpenAI",
            "aliases": ["GPT"],
            "expected": True
        },
        {
            "category": "Partial Match",
            "text": "The Pinecone vector database offers",
            "brand": "Pinecone",
            "aliases": [],
            "expected": True
        },
        
        # Alias/product matches
        {
            "category": "Alias Match",
            "text": "ChatGPT is widely used",
            "brand": "OpenAI",
            "aliases": ["ChatGPT", "GPT", "DALL-E"],
            "expected": True
        },
        {
            "category": "Alias Match",
            "text": "Using Claude for coding",
            "brand": "Anthropic",
            "aliases": ["Claude", "Claude 3"],
            "expected": True
        },
        
        # Contextual references
        {
            "category": "Contextual",
            "text": "The company behind ChatGPT announced",
            "brand": "OpenAI",
            "aliases": ["ChatGPT"],
            "expected": True
        },
        
        # Case variations
        {
            "category": "Case Variation",
            "text": "OPENAI leads in AI research",
            "brand": "OpenAI",
            "aliases": [],
            "expected": True
        },
        {
            "category": "Case Variation",
            "text": "pinecone is a vector db",
            "brand": "Pinecone",
            "aliases": [],
            "expected": True
        },
        
        # Negative cases - should NOT match
        {
            "category": "No Match",
            "text": "Microsoft Azure cloud platform",
            "brand": "OpenAI",
            "aliases": ["ChatGPT"],
            "expected": False
        },
        {
            "category": "No Match",
            "text": "AWS provides cloud services",
            "brand": "Pinecone",
            "aliases": [],
            "expected": False
        },
        {
            "category": "No Match",
            "text": "Google released Gemini",
            "brand": "OpenAI",
            "aliases": ["ChatGPT", "GPT"],
            "expected": False
        },
        
        # Tricky cases
        {
            "category": "Tricky",
            "text": "Open-source AI models are popular",
            "brand": "OpenAI",
            "aliases": [],
            "expected": False  # "Open" in "Open-source" != OpenAI
        },
        {
            "category": "Tricky",
            "text": "The pine cone fell from the tree",
            "brand": "Pinecone",
            "aliases": [],
            "expected": False  # Natural pine cone != Pinecone company
        },
    ]
    
    results = {"passed": 0, "failed": 0}
    
    for test in test_cases:
        result = await evaluator.match_brand(
            test["text"],
            test["brand"],
            test["aliases"]
        )
        
        is_match = result.is_match and result.confidence >= 0.7
        correct = is_match == test["expected"]
        
        if correct:
            results["passed"] += 1
            status = "✓ PASS"
        else:
            results["failed"] += 1
            status = "✗ FAIL"
        
        print(f"\n[{test['category']}] {status}")
        print(f"  Text: \"{test['text'][:50]}{'...' if len(test['text']) > 50 else ''}\"")
        print(f"  Brand: {test['brand']}")
        print(f"  Expected: {test['expected']}, Got: {is_match}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning[:100]}...")
    
    print("\n" + "=" * 60)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")
    print(f"Accuracy: {results['passed'] / len(test_cases) * 100:.1f}%")
    print("=" * 60)
    
    return results["failed"] == 0


async def test_output_evaluation():
    """Test semantic output evaluation"""
    from llm_evaluator import LLMEvaluator, EvaluationConfig, EvaluatorBackend
    
    print("\n" + "=" * 60)
    print("LLM-as-a-Judge Output Evaluation Tests")
    print("=" * 60)
    
    evaluator = LLMEvaluator(EvaluationConfig(
        backend=EvaluatorBackend.OPENAI
    ))
    
    test_cases = [
        {
            "expected": "OpenAI is a leading AI research company",
            "actual": "OpenAI is one of the top artificial intelligence research organizations",
            "criteria": "semantic similarity",
            "should_pass": True
        },
        {
            "expected": "Python is a programming language",
            "actual": "Python is a popular programming language used for web development",
            "criteria": "factual accuracy",
            "should_pass": True
        },
        {
            "expected": "The capital of France is Paris",
            "actual": "The capital of France is London",
            "criteria": "factual accuracy",
            "should_pass": False
        },
        {
            "expected": "Machine learning requires training data",
            "actual": "ML models need datasets for training",
            "criteria": "semantic equivalence",
            "should_pass": True
        },
    ]
    
    results = {"passed": 0, "failed": 0}
    
    for test in test_cases:
        result = await evaluator.evaluate_output(
            test["expected"],
            test["actual"],
            test["criteria"]
        )
        
        correct = result.passed == test["should_pass"]
        
        if correct:
            results["passed"] += 1
            status = "✓ PASS"
        else:
            results["failed"] += 1
            status = "✗ FAIL"
        
        print(f"\n{status}")
        print(f"  Expected: \"{test['expected'][:40]}...\"")
        print(f"  Actual: \"{test['actual'][:40]}...\"")
        print(f"  Criteria: {test['criteria']}")
        print(f"  Result: passed={result.passed}, score={result.score:.2f}")
        print(f"  Feedback: {result.feedback[:100]}...")
    
    print("\n" + "=" * 60)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)
    
    return results["failed"] == 0


async def test_batch_matching():
    """Test batch brand matching efficiency"""
    from llm_evaluator import LLMEvaluator, EvaluationConfig, EvaluatorBackend
    
    print("\n" + "=" * 60)
    print("Batch Brand Matching Test")
    print("=" * 60)
    
    evaluator = LLMEvaluator(EvaluationConfig(
        backend=EvaluatorBackend.OPENAI
    ))
    
    # Test text mentioning multiple brands
    text = "OpenAI and Anthropic are leading AI companies, while Pinecone provides vector database solutions."
    
    brands = [
        {"name": "OpenAI", "aliases": ["ChatGPT"]},
        {"name": "Anthropic", "aliases": ["Claude"]},
        {"name": "Pinecone", "aliases": []},
        {"name": "Google", "aliases": ["Gemini"]},
    ]
    
    results = await evaluator.match_brands_batch(text, brands)
    
    print(f"\nText: \"{text}\"")
    print("\nBrand Matches:")
    
    for r in results:
        status = "✓" if r["is_match"] else "✗"
        print(f"  {status} {r['brand']['name']}: "
              f"match={r['is_match']}, confidence={r['confidence']:.2f}")
        if r["is_match"]:
            print(f"      Matched: \"{r['matched_text']}\"")
    
    # Verify expected matches
    expected_matches = {"OpenAI", "Anthropic", "Pinecone"}
    actual_matches = {r["brand"]["name"] for r in results if r["is_match"]}
    
    if expected_matches == actual_matches:
        print("\n✓ All expected brands matched correctly!")
        return True
    else:
        print(f"\n✗ Mismatch! Expected: {expected_matches}, Got: {actual_matches}")
        return False


async def compare_regex_vs_llm():
    """Compare regex matching vs LLM matching"""
    print("\n" + "=" * 60)
    print("Regex vs LLM Matching Comparison")
    print("=" * 60)
    
    # Import both matchers
    from run import match_brand
    from llm_evaluator import LLMEvaluator, EvaluationConfig, EvaluatorBackend
    
    evaluator = LLMEvaluator(EvaluationConfig(
        backend=EvaluatorBackend.OPENAI,
        confidence_threshold=0.7
    ))
    
    # Test cases where LLM should outperform regex
    test_cases = [
        {
            "text": "OpenAI's latest model",
            "brand": {"name": "OpenAI", "aliases": []},
            "regex_should_match": False,  # Regex won't match "OpenAI's"
            "llm_should_match": True
        },
        {
            "text": "The ChatGPT team announced",
            "brand": {"name": "OpenAI", "aliases": ["ChatGPT"]},
            "regex_should_match": False,  # Text is "The ChatGPT team", not just "ChatGPT"
            "llm_should_match": True
        },
        {
            "text": "Pinecone vector DB",
            "brand": {"name": "Pinecone", "aliases": []},
            "regex_should_match": False,  # "Pinecone vector DB" != "Pinecone"
            "llm_should_match": True
        },
    ]
    
    print("\n{:<40} {:>12} {:>12}".format("Text", "Regex", "LLM"))
    print("-" * 66)
    
    for test in test_cases:
        # Regex match
        regex_match = match_brand(test["text"], test["brand"]) is not None
        
        # LLM match
        result = await evaluator.match_brand(
            test["text"],
            test["brand"]["name"],
            test["brand"].get("aliases", [])
        )
        llm_match = result.is_match and result.confidence >= 0.7
        
        regex_status = "✓" if regex_match else "✗"
        llm_status = "✓" if llm_match else "✗"
        
        print(f"{test['text'][:38]:<40} {regex_status:>12} {llm_status:>12}")
    
    print("\nConclusion: LLM matching handles partial matches and context better!")


async def main():
    """Run all LLM evaluator tests"""
    print("\n" + "=" * 60)
    print("LLM-as-a-Judge Evaluation Test Suite")
    print("Uses GPT-4o-mini for cheap, fast evaluation")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    if not await test_brand_matching():
        all_passed = False
    
    if not await test_output_evaluation():
        all_passed = False
    
    if not await test_batch_matching():
        all_passed = False
    
    await compare_regex_vs_llm()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All LLM evaluator tests passed!")
    else:
        print("✗ Some tests failed. Review output above.")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
