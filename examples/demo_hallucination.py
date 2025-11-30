"""
Hallucination Filter Demo

This script demonstrates the hallucination filter feature by:
1. Running a small analysis with source collection
2. Analyzing hallucination risks
3. Showing the results

This is a simplified demo - in production you'd run against your full query set.
"""

import asyncio
import json
import sqlite3
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from providers.openai_provider_with_sources import OpenAIProviderWithSources
from hallucination_filter import (
    SourceValidator, 
    HallucinationScorer,
    create_hallucination_tables
)


async def demo():
    print("="*70)
    print("HALLUCINATION FILTER DEMO")
    print("="*70)
    print()
    
    # Create a demo query
    query = "What are the best AI companies for enterprise automation?"
    k = 5
    
    print(f"Query: {query}")
    print(f"Requesting top {k} results with sources and confidence scores...\n")
    
    # Initialize provider with source support
    try:
        provider = OpenAIProviderWithSources(model="gpt-5-nano-2025-08-07")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease set OPENAI_API_KEY in your environment:")
        print("  export OPENAI_API_KEY='your-key-here'")
        return
    
    # Get results
    print("🔄 Querying LLM...")
    try:
        result = await provider.rank(query, k)
    except Exception as e:
        print(f"❌ Error querying LLM: {e}")
        return
    
    print("✅ Response received!\n")
    
    # Display results with sources and confidence
    print("="*70)
    print("RESULTS WITH SOURCE ATTRIBUTION")
    print("="*70)
    
    answers = result.get("answers", [])
    
    for idx, answer in enumerate(answers, 1):
        name = answer.get("name", "Unknown")
        why = answer.get("why", "")
        sources = answer.get("sources", [])
        confidence = answer.get("confidence", 0.0)
        
        print(f"\n#{idx} - {name}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Reason: {why[:150]}...")
        
        if sources:
            print(f"Sources ({len(sources)}):")
            for source in sources[:3]:  # Show first 3 sources
                url = source.get("url", "")
                title = source.get("title", "")
                if title:
                    print(f"  • {title}")
                    print(f"    {url}")
                else:
                    print(f"  • {url}")
        else:
            print("⚠️  No sources provided")
    
    # Validate sources
    print("\n" + "="*70)
    print("SOURCE VALIDATION")
    print("="*70)
    
    validator = SourceValidator()
    all_sources = []
    
    for answer in answers:
        all_sources.extend(answer.get("sources", []))
    
    if all_sources:
        print(f"\n🔄 Validating {len(all_sources)} URLs...")
        validation_results = await validator.validate_sources(all_sources)
        
        valid_count = sum(1 for r in validation_results if isinstance(r, dict) and r.get("is_valid"))
        accessible_count = sum(1 for r in validation_results if isinstance(r, dict) and r.get("is_accessible"))
        
        print(f"✅ Valid URLs: {valid_count}/{len(all_sources)}")
        print(f"✅ Accessible URLs: {accessible_count}/{len(all_sources)}")
        
        # Show any problematic URLs
        problems = [r for r in validation_results if isinstance(r, dict) and not r.get("is_accessible")]
        if problems:
            print(f"\n⚠️  Issues found with {len(problems)} URLs:")
            for r in problems[:3]:
                print(f"  • {r['url'][:60]}...")
                print(f"    Error: {r.get('error', 'Not accessible')}")
    else:
        print("\n⚠️  No sources to validate")
    
    # Calculate reliability scores
    print("\n" + "="*70)
    print("HALLUCINATION RISK ANALYSIS")
    print("="*70)
    
    scorer = HallucinationScorer()
    
    print()
    for idx, answer in enumerate(answers, 1):
        name = answer.get("name", "Unknown")
        sources = answer.get("sources", [])
        confidence = answer.get("confidence", 0.5)
        
        # Check if sources are accessible
        source_accessible = False
        if sources:
            source_urls = [s.get("url", "") for s in sources]
            for url in source_urls:
                if url in validator.cache and validator.cache[url].get("is_accessible"):
                    source_accessible = True
                    break
        
        # Calculate reliability
        score_result = scorer.calculate_reliability_score(
            has_source=len(sources) > 0,
            source_accessible=source_accessible,
            confidence=confidence,
            source_count=len(sources)
        )
        
        # Display with emoji based on risk
        risk_emoji = {
            "low": "🟢",
            "medium": "🟡", 
            "high": "🔴"
        }
        
        emoji = risk_emoji.get(score_result["risk_level"], "⚪")
        
        print(f"{emoji} #{idx} - {name}")
        print(f"   Reliability Score: {score_result['reliability_score']:.2f}")
        print(f"   Risk Level: {score_result['risk_level'].upper()}")
        print(f"   Has Sources: {len(sources) > 0} ({len(sources)} sources)")
        print(f"   Accessible: {source_accessible}")
        print(f"   Confidence: {confidence:.2f}")
        print()
    
    # Summary
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for answer in answers:
        sources = answer.get("sources", [])
        confidence = answer.get("confidence", 0.5)
        
        source_accessible = False
        if sources:
            source_urls = [s.get("url", "") for s in sources]
            for url in source_urls:
                if url in validator.cache and validator.cache[url].get("is_accessible"):
                    source_accessible = True
                    break
        
        score_result = scorer.calculate_reliability_score(
            has_source=len(sources) > 0,
            source_accessible=source_accessible,
            confidence=confidence,
            source_count=len(sources)
        )
        risk_counts[score_result["risk_level"]] += 1
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n🟢 Low Risk (Reliable): {risk_counts['low']}/{len(answers)}")
    print(f"🟡 Medium Risk: {risk_counts['medium']}/{len(answers)}")
    print(f"🔴 High Risk (Potential Hallucination): {risk_counts['high']}/{len(answers)}")
    
    if risk_counts['high'] > 0:
        print("\n⚠️  Warning: Some results have high hallucination risk!")
        print("   Consider using results with verified sources only.")
    else:
        print("\n✅ All results have low-to-medium risk!")
    
    print("\n" + "="*70)
    print("\nNext steps:")
    print("  1. Run full analysis: python foundamental.py run --with-sources")
    print("  2. Analyze risks: python foundamental.py hallucination --analyze --verify-urls")
    print("  3. View report: python foundamental.py hallucination --report")
    print()


if __name__ == "__main__":
    asyncio.run(demo())
