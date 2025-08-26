#!/usr/bin/env python3
"""
LLM SEO Test Suite
Tests all components of the LLM SEO application to ensure BAML integration is working
"""
# Import required packages
import asyncio
import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))
load_dotenv()


def test_imports():
    """Test that all required imports work"""
    print("Testing imports...")

    try:
        from baml_client import b
        from baml_client.types import RankingResult, SentimentResult, Answer, Sentiment
        print("BAML client and types imported successfully")
    except ImportError as e:
        print(f"BAML import failed: {e}")
        print("Run: pip install baml-py==0.205.0")
        return False

    try:
        from src.providers.openai_provider import OpenAIProvider
        from src.providers.ollama_provider import OllamaProvider
        from src.providers.base import LLMProvider
        print("Provider classes imported successfully")
    except ImportError as e:
        print(f"Provider import failed: {e}")
        return False

    try:
        import src.run as run
        import src.analyze as analyze
        print("Main modules imported successfully")
    except ImportError as e:
        print(f"Module import failed: {e}")
        return False

    return True


async def test_baml_functions():
    """Test BAML functions directly"""
    print("\n Testing BAML functions...")

    try:
        from baml_client.async_client import b
        print("Testing RankEntitiesOpenAI...")
        try:
            result = await b.RankEntitiesOpenAI(
                query="Best AI frameworks for testing",
                k=3
            )
            print(f"Got {len(result.answers)} answers")
            if result.answers:
                print(f"First answer: {result.answers[0].name}")
        except Exception as e:
            print(f"RankEntitiesOpenAI failed: {e}")
            print("Check your OpenAI API key in .env file")
            return False

        print("Testing BrandSentiment...")
        try:
            sentiment = await b.BrandSentiment(
                brand="TestBrand",
                passage="TestBrand has excellent customer support and innovative features."
            )
            print(
                f"Sentiment: {sentiment.sentiment.value} (confidence: {sentiment.confidence:.2f})")
        except Exception as e:
            print(f"BrandSentiment failed: {e}")
            return False

    except Exception as e:
        print(f"BAML function test failed: {e}")
        return False

    return True


async def test_providers():
    """Test provider classes"""
    print("\n Testing provider classes...")

    from src.providers.openai_provider import OpenAIProvider

    try:
        print("Testing OpenAIProvider...")
        openai_provider = OpenAIProvider(model="gpt-4o-mini")

        result = await openai_provider.rank("Best testing frameworks", 2)

        if "answers" in result and len(result["answers"]) > 0:
            print(f"Got {len(result['answers'])} answers from OpenAI")
            print(f"First answer: {result['answers'][0]['name']}")
        else:
            print("No answers received from OpenAI provider")
            return False

    except Exception as e:
        print(f"OpenAI provider test failed: {e}")
        print("Check your OpenAI API key in .env file")
        return False

    # Test Ollama provider (may fail if Ollama not running)
    # That is fine for now if you don't have it set up
    try:
        from src.providers.ollama_provider import OllamaProvider
        print("Testing OllamaProvider...")
        ollama_provider = OllamaProvider(model="llama3")

        result = await ollama_provider.rank("Best testing frameworks", 2)

        if "answers" in result and len(result["answers"]) > 0:
            print(f"Got {len(result['answers'])} answers from Ollama")
        else:
            print("Ollama test failed (Ollama may not be running)")

    except Exception as e:
        print(f"Ollama provider test failed: {e}")
        print("This is OK if Ollama is not running locally")

    return True


def test_database_operations():
    """Test database operations"""
    print("\n Testing database operations...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        test_db = tmp.name

    try:
        from src.run import create_tables, match_brand
        conn = sqlite3.connect(test_db)
        create_tables(conn)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        expected_tables = ['responses', 'mentions', 'runs']

        if all(table in tables for table in expected_tables):
            print("Database tables created successfully")
        else:
            print(f"Missing tables. Got: {tables}")
            return False
        test_brand = {"id": 1, "name": "TestBrand",
                      "aliases": ["TB", "Test Brand"]}

        if match_brand("TestBrand", test_brand) == "TestBrand":
            print("Brand matching works correctly")
        else:
            print("Brand matching failed")
            return False

        conn.close()

    except Exception as e:
        print(f"Database test failed: {e}")
        return False

    finally:
        if os.path.exists(test_db):
            os.unlink(test_db)

    return True


def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")

    try:
        from src.run import load_config

        config = load_config("nonexistent_config.json")

        if "brands" in config and "queries" in config:
            print(
                f"Default config loaded with {len(config['brands'])} brands and {len(config['queries'])} queries")
        else:
            print("Configuration structure is invalid")
            return False

        if os.path.exists("config.json"):
            config = load_config("config.json")
            print(
                f"Loaded config.json with {len(config['brands'])} brands and {len(config['queries'])} queries")

    except Exception as e:
        print(f"Configuration test failed: {e}")
        return False

    return True


async def run_integration_test():
    """Run a mini integration test"""
    print("\n Running integration test...")

    try:
        from src.run import BRANDS, QUERIES, PROVIDERS
        import tempfile
        import sqlite3
        import json
        import time

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            test_db = tmp.name

        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        from src.run import create_tables, match_brand
        create_tables(conn)

        provider = PROVIDERS[0]  # OpenAI provider
        query = QUERIES[0]       # First query

        print(f"Testing: {provider.name} with query '{query['text'][:30]}...'")

        try:
            result = await provider.rank(query["text"], min(query["k"], 2))

            if "answers" in result and result["answers"]:
                print(f"Got {len(result['answers'])} answers")
                c.execute('''INSERT INTO responses (query_id, provider_name, model_name, raw_response, timestamp)
                            VALUES (?, ?, ?, ?, ?)''',
                          (query["id"], provider.name, getattr(provider, 'model', 'unknown'),
                           json.dumps(result), time.time()))
                response_id = c.lastrowid
                mentions_found = 0
                for idx, answer in enumerate(result["answers"]):
                    for brand in BRANDS:
                        alias = match_brand(answer.get("name", ""), brand)
                        if alias:
                            mentions_found += 1
                            print(f"Found {brand['name']} at rank #{idx + 1}")

                print(
                    f"Integration test completed - found {mentions_found} brand mentions")

            else:
                print("No answers received in integration test")
                return False

        except Exception as e:
            print(f"Integration test failed: {e}")
            return False
        finally:
            conn.close()
            if os.path.exists(test_db):
                os.unlink(test_db)

    except Exception as e:
        print(f"Integration test setup failed: {e}")
        return False

    return True


async def main():
    """Run all tests"""
    print("LLM SEO Test Suite")
    print("=" * 50)

    if not os.path.exists(".env"):
        print("Warning: .env file not found. Some tests may fail.")
        print("   Create .env with your OPENAI_API_KEY for full testing.")

    tests = [
        ("Import Test", test_imports, False),
        ("BAML Functions", test_baml_functions, True),
        ("Provider Classes", test_providers, True),
        ("Database Operations", test_database_operations, False),
        ("Configuration", test_configuration, False),
        ("Integration Test", run_integration_test, True),
    ]

    passed = 0
    failed = 0

    for test_name, test_func, is_async in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            if is_async:
                result = await test_func()
            else:
                result = test_func()

            if result:
                passed += 1
                print(f"{test_name} PASSED")
            else:
                failed += 1
                print(f"{test_name} FAILED")

        except Exception as e:
            failed += 1
            print(f"{test_name} FAILED with exception: {e}")

    print(f"\n Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("All tests passed!")
        print("\nNext steps:")
        print("  1. python foundamental.py run")
        print("  2. python foundamental.py analyze --report")
        print("  3. python foundamental.py sentiment --analyze")
    else:
        print("Some tests failed. Please address the issues above.")

    return failed == 0


if __name__ == "__main__":
    asyncio.run(main())
