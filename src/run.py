# Import Required Packages
import re
import asyncio
import time
import json
import sqlite3
import os
from pathlib import Path
from providers.openai_provider import OpenAIProvider
from providers.ollama_provider import OllamaProvider

# LLM Evaluator for semantic brand matching
USE_LLM_MATCHING = os.getenv("USE_LLM_MATCHING", "false").lower() == "true"
_llm_evaluator = None


def get_llm_evaluator():
    """Lazy initialization of LLM evaluator"""
    global _llm_evaluator
    if _llm_evaluator is None:
        from llm_evaluator import LLMEvaluator, EvaluationConfig, EvaluatorBackend
        backend = EvaluatorBackend.OPENAI if os.getenv("LLM_EVAL_BACKEND", "openai") == "openai" else EvaluatorBackend.OLLAMA
        _llm_evaluator = LLMEvaluator(EvaluationConfig(
            backend=backend,
            confidence_threshold=float(os.getenv("LLM_EVAL_THRESHOLD", "0.7")),
            fallback_to_regex=True
        ))
    return _llm_evaluator


def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    if not os.path.exists(config_path):
        return {
            "brands": [
                {"id": 1, "name": "YourBrand",
                    "aliases": ["Your Brand", "YB"]},
                {"id": 2, "name": "CompetitorX", "aliases": ["Comp X", "CX"]},
            ],
            "queries": [
                {"id": 1, "text": "Best vector database for RAG", "k": 5},
                {"id": 2, "text": "Top enterprise chatbots for internal knowledge", "k": 5},
            ]
        }

    with open(config_path, 'r') as f:
        return json.load(f)


config = load_config()
BRANDS = config["brands"]
QUERIES = config["queries"]

PROVIDERS = [
    OpenAIProvider(model="gpt-5-nano-2025-08-07"),
    OllamaProvider(model="llama3"),
]


def match_brand(name: str, brand):
    """
    Simple exact-match brand matching (regex-based).
    For semantic matching, use match_brand_llm instead.
    """
    target = name.lower()
    if brand["name"].lower() == target:
        return brand["name"]
    for alias in brand["aliases"]:
        if alias.lower() == target:
            return alias
    return None


async def match_brand_llm(name: str, brand):
    """
    LLM-powered semantic brand matching.
    Uses cheap models (GPT-5 nano or Ollama) to evaluate matches.
    
    Can recognize:
    - Partial mentions ("OpenAI's latest model" -> OpenAI)
    - Misspellings 
    - Contextual references
    - Abbreviations
    
    Returns:
        Tuple of (alias, confidence, reasoning) or (None, None, None)
    """
    evaluator = get_llm_evaluator()
    result = await evaluator.match_brand(
        text=name,
        brand_name=brand["name"],
        brand_aliases=brand.get("aliases", [])
    )
    
    if result.is_match and result.confidence >= evaluator.config.confidence_threshold:
        return (result.matched_alias or brand["name"], result.confidence, result.reasoning)
    return (None, result.confidence if result else 0.0, result.reasoning if result else None)


def create_tables(conn):
    """Create database tables if they don't exist"""
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_id INTEGER,
        provider_name TEXT,
        model_name TEXT,
        raw_response TEXT,
        timestamp REAL,
        error_message TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS mentions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        response_id INTEGER,
        brand_id INTEGER,
        brand_name TEXT,
        alias_used TEXT,
        rank_position INTEGER,
        explanation TEXT,
        timestamp REAL,
        match_method TEXT DEFAULT 'regex',
        match_confidence REAL,
        match_reasoning TEXT,
        FOREIGN KEY (response_id) REFERENCES responses (id)
    )''')
    
    # LLM evaluation statistics table
    c.execute('''CREATE TABLE IF NOT EXISTS evaluation_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        eval_method TEXT,
        total_evaluations INTEGER,
        avg_confidence REAL,
        high_confidence_count INTEGER,
        low_confidence_count INTEGER,
        fallback_count INTEGER,
        timestamp REAL,
        FOREIGN KEY (run_id) REFERENCES runs (id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at REAL,
        completed_at REAL,
        total_queries INTEGER,
        total_providers INTEGER,
        success_count INTEGER,
        error_count INTEGER
    )''')

    conn.commit()


async def main():
    conn = sqlite3.connect("llmseo.db")
    c = conn.cursor()

    create_tables(conn)

    run_started = time.time()
    run_id = None
    success_count = 0
    error_count = 0
    total_operations = len(PROVIDERS) * len(QUERIES)
    
    # LLM evaluation tracking
    eval_stats = {
        "total_evaluations": 0,
        "confidence_sum": 0.0,
        "high_confidence_count": 0,
        "low_confidence_count": 0,
        "fallback_count": 0
    }

    c.execute('''INSERT INTO runs (started_at, total_queries, total_providers, success_count, error_count)
                 VALUES (?, ?, ?, 0, 0)''',
              (run_started, len(QUERIES), len(PROVIDERS)))
    run_id = c.lastrowid

    match_method = "llm" if USE_LLM_MATCHING else "regex"
    print(f"Starting LLM SEO analysis with {len(PROVIDERS)} providers and {len(QUERIES)} queries...")
    print(f"Match method: {match_method.upper()}")

    for provider_idx, provider in enumerate(PROVIDERS):
        print(f"Provider {provider_idx + 1}/{len(PROVIDERS)}: {provider.name}")

        for query_idx, q in enumerate(QUERIES):
            print(f"Query {query_idx + 1}/{len(QUERIES)}: {q['text'][:50]}...")

            try:
                res = await provider.rank(q["text"], q["k"])
                answers = res.get("answers", [])
                raw = json.dumps(res)
                c.execute('''INSERT INTO responses (query_id, provider_name, model_name, raw_response, timestamp)
                            VALUES (?, ?, ?, ?, ?)''',
                          (q["id"], provider.name, getattr(provider, 'model', 'unknown'),
                           raw, time.time()))
                response_id = c.lastrowid
                mentions_found = 0
                for idx, a in enumerate(answers):
                    answer_name = a.get("name", "")
                    answer_why = a.get("why", "")

                    for brand in BRANDS:
                        # Use LLM matching if enabled, otherwise regex
                        if USE_LLM_MATCHING:
                            alias, confidence, reasoning = await match_brand_llm(answer_name, brand)
                            eval_stats["total_evaluations"] += 1
                            if confidence:
                                eval_stats["confidence_sum"] += confidence
                                if confidence >= 0.8:
                                    eval_stats["high_confidence_count"] += 1
                                elif confidence < 0.5:
                                    eval_stats["low_confidence_count"] += 1
                        else:
                            alias = match_brand(answer_name, brand)
                            confidence = 1.0 if alias else 0.0
                            reasoning = "Exact match" if alias else None
                        
                        if alias:
                            mentions_found += 1
                            c.execute('''INSERT INTO mentions 
                                        (response_id, brand_id, brand_name, alias_used, rank_position, 
                                         explanation, timestamp, match_method, match_confidence, match_reasoning)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                      (response_id, brand["id"], brand["name"], alias,
                                       idx + 1, answer_why, time.time(), match_method, confidence, reasoning))

                            if USE_LLM_MATCHING:
                                print(f"Found {brand['name']} (as '{alias}') at rank #{idx + 1} [confidence: {confidence:.2f}]")
                            else:
                                print(f"Found {brand['name']} (as '{alias}') at rank #{idx + 1}")

                if mentions_found == 0:
                    print(f"No brand mentions found in top {q['k']} results")

                success_count += 1

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                print(f"Error: {error_msg}")
                c.execute('''INSERT INTO responses (query_id, provider_name, model_name, timestamp, error_message)
                            VALUES (?, ?, ?, ?, ?)''',
                          (q["id"], provider.name, getattr(provider, 'model', 'unknown'),
                           time.time(), error_msg))

    run_completed = time.time()
    c.execute('''UPDATE runs SET completed_at = ?, success_count = ?, error_count = ?
                 WHERE id = ?''',
              (run_completed, success_count, error_count, run_id))
    
    # Save evaluation stats if LLM matching was used
    if USE_LLM_MATCHING and eval_stats["total_evaluations"] > 0:
        avg_confidence = eval_stats["confidence_sum"] / eval_stats["total_evaluations"]
        c.execute('''INSERT INTO evaluation_stats 
                    (run_id, eval_method, total_evaluations, avg_confidence, 
                     high_confidence_count, low_confidence_count, fallback_count, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (run_id, "llm", eval_stats["total_evaluations"], avg_confidence,
                   eval_stats["high_confidence_count"], eval_stats["low_confidence_count"],
                   eval_stats["fallback_count"], time.time()))

    conn.commit()
    conn.close()

    duration = run_completed - run_started
    print(f"\n Analysis Complete!")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Success: {success_count}/{total_operations}")
    print(f"   Errors: {error_count}/{total_operations}")
    print(f"   Match Method: {match_method.upper()}")
    if USE_LLM_MATCHING and eval_stats["total_evaluations"] > 0:
        avg_conf = eval_stats["confidence_sum"] / eval_stats["total_evaluations"]
        print(f"   LLM Evaluations: {eval_stats['total_evaluations']}")
        print(f"   Avg Confidence: {avg_conf:.2f}")
    print(f"   Database: llmseo.db")

if __name__ == "__main__":
    asyncio.run(main())
