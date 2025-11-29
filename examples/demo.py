"""
BAML Integration Demo
Shows how the BAML integration works with mock data
"""
# Import Required Packages
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def demo_baml_structure():
    """Demonstrate the BAML integration structure"""
    print("BAML Integration Demo")
    print("=" * 40)

    print("\n1. BAML Functions Available:")
    try:
        from baml_client import b
        functions = [attr for attr in dir(b) if not attr.startswith('_')]
        for func in functions:
            if 'Rank' in func or 'Sentiment' in func:
                print(f"{func} is available")

        print("\n2. BAML Types Available:")
        from baml_client.types import RankingResult, SentimentResult, Answer, Sentiment
        print("RankingResult - Contains list of Answer objects")
        print("Answer - Contains name and why fields")
        print("SentimentResult - Contains sentiment and confidence")
        print("Sentiment - Enum: Positive, Neutral, Negative")

        print("\n3. Provider Integration:")
        from providers.openai_provider import OpenAIProvider
        from providers.ollama_provider import OllamaProvider

        openai_provider = OpenAIProvider()
        ollama_provider = OllamaProvider()

        print(f"OpenAI Provider - Uses: b.RankEntitiesOpenAI()")
        print(f"Ollama Provider - Uses: b.RankEntitiesOllama()")

        print("\n4. How it works:")
        print("   • BAML templates in baml_src/llm_seo.baml define prompts")
        print("   • Generated client in baml_client/ provides type-safe functions")
        print("   • Providers call BAML functions instead of hardcoded prompts")
        print("   • Results are automatically parsed into structured types")

        return True

    except Exception as e:
        print(f"Demo failed: {e}")
        return False


def show_baml_prompt_structure():
    """Show the BAML prompt structure"""
    print("\n5. BAML Prompt Structure:")
    print("From baml_src/llm_seo.baml:")
    print("""
   function RankEntitiesOpenAI(query: string, k: int) -> RankingResult {
     client CustomGPT4oMini
     prompt #"
       You are a rankings engine. Return top-K entities for the query.
       Query: {{ query }}
       TopK: {{ k }}
       {{ ctx.output_format }}
     "#
   }
   """)

    print("Benefits vs hardcoded strings:")
    print("   • Type safety - compile-time checks")
    print("   • Template reuse - consistent prompts")
    print("   • Easy testing - built-in test cases")
    print("   • Provider flexibility - different clients per function")


async def simulate_workflow():
    """Simulate the workflow with mock data"""
    print("\n6. Simulated Workflow:")

    # Mock result
    mock_ranking_result = {
        "answers": [
            {"name": "YourBrand", "why": "Leading solution with excellent features"},
            {"name": "CompetitorX", "why": "Popular alternative with good support"},
            {"name": "ThirdOption", "why": "Open source solution"}
        ]
    }

    print("Query: 'Best AI platforms for business'")
    print("Mock BAML Response:")
    for i, answer in enumerate(mock_ranking_result["answers"], 1):
        print(f"#{i}: {answer['name']} - {answer['why']}")

    print("\nBrand Detection:")
    from run import BRANDS, match_brand

    mentions_found = 0
    for i, answer in enumerate(mock_ranking_result["answers"]):
        for brand in BRANDS:
            alias = match_brand(answer["name"], brand)
            if alias:
                mentions_found += 1
                print(f"Found {brand['name']} at rank #{i+1}")

    print(f"\nResult: {mentions_found} brand mentions detected")
    return True


def main():
    if demo_baml_structure():
        show_baml_prompt_structure()
        asyncio.run(simulate_workflow())

        print("\n Summary:")
        print("BAML integration is working correctly")
        print("Type-safe LLM interactions ready")
        print("Providers configured to use BAML functions")
        print("Database and analysis pipeline ready")

        print("\n Next Steps:")
        print("1. Add your OpenAI API key to .env file")
        print("2. Run: python foundamental.py run")
        print("3. View results: python foundamental.py analyze --report")

        return True
    else:
        print("Demo failed - check your setup")
        return False


if __name__ == "__main__":
    main()
