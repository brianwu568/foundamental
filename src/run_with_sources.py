# Import Required Packages
"""
Run LLM SEO analysis with Hallucination Filter support

This module runs brand visibility analysis with optional hallucination detection.
It can collect sources and confidence scores from LLMs to verify claims.
Co-mention relationships are automatically tracked for competitor graph analysis.
"""
import re
import asyncio
import time
import json
import sqlite3
import os
from pathlib import Path
from providers.openai_provider import OpenAIProvider
from providers.ollama_provider import OllamaProvider
from providers.openai_provider_with_sources import OpenAIProviderWithSources
from providers.ollama_provider_with_sources import OllamaProviderWithSources
import sys


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


def get_providers(with_sources=False):
    """Get list of providers based on mode"""
    if with_sources:
        return [
            OpenAIProviderWithSources(model="gpt-5-nano-2025-08-07"),
            OllamaProviderWithSources(model="llama3"),
        ]
    else:
        return [
            OpenAIProvider(model="gpt-5-nano-2025-08-07"),
            OllamaProvider(model="llama3"),
        ]


def match_brand(name: str, brand):
    target = name.lower()
    if brand["name"].lower() == target:
        return brand["name"]
    for alias in brand["aliases"]:
        if alias.lower() == target:
            return alias
    return None


def extract_co_mentions_for_response(conn, response_id, mentioned_brands, 
                                     query_id, provider_name, model_name, timestamp):
    """
    Extract co-mention relationships from a response
    
    Args:
        conn: Database connection
        response_id: ID of the response
        mentioned_brands: List of tuples (brand_id, brand_name, rank_position)
        query_id: ID of the query
        provider_name: Name of the provider
        model_name: Name of the model
        timestamp: Timestamp of the response
    """
    if len(mentioned_brands) < 2:
        return 0
    
    c = conn.cursor()
    co_mentions_added = 0
    
    # Create co-mention pairs (ensuring brand_id_1 < brand_id_2)
    for i in range(len(mentioned_brands)):
        for j in range(i + 1, len(mentioned_brands)):
            brand1 = mentioned_brands[i]
            brand2 = mentioned_brands[j]
            
            # Ensure consistent ordering
            if brand1[0] < brand2[0]:
                b1_id, b1_name, b1_rank = brand1
                b2_id, b2_name, b2_rank = brand2
            else:
                b2_id, b2_name, b2_rank = brand1
                b1_id, b1_name, b1_rank = brand2
            
            rank_distance = abs(b1_rank - b2_rank)
            
            c.execute('''
                INSERT INTO co_mentions 
                (response_id, brand_id_1, brand_id_2, brand_name_1, brand_name_2,
                 rank_1, rank_2, rank_distance, query_id, provider_name, 
                 model_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (response_id, b1_id, b2_id, b1_name, b2_name,
                  b1_rank, b2_rank, rank_distance, query_id,
                  provider_name, model_name, timestamp))
            
            co_mentions_added += 1
    
    return co_mentions_added


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
        FOREIGN KEY (response_id) REFERENCES responses (id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at REAL,
        completed_at REAL,
        total_queries INTEGER,
        total_providers INTEGER,
        success_count INTEGER,
        error_count INTEGER,
        with_sources BOOLEAN
    )''')
    
    # Hallucination filter tables
    c.execute('''CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mention_id INTEGER,
        url TEXT,
        title TEXT,
        description TEXT,
        is_valid BOOLEAN,
        is_accessible BOOLEAN,
        status_code INTEGER,
        content_type TEXT,
        validation_error TEXT,
        timestamp REAL,
        FOREIGN KEY (mention_id) REFERENCES mentions (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS hallucination_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mention_id INTEGER,
        confidence_score REAL,
        reliability_score REAL,
        risk_level TEXT,
        has_source BOOLEAN,
        source_accessible BOOLEAN,
        source_count INTEGER,
        timestamp REAL,
        FOREIGN KEY (mention_id) REFERENCES mentions (id)
    )''')
    
    # Competitor graph tables
    c.execute('''CREATE TABLE IF NOT EXISTS co_mentions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        response_id INTEGER,
        brand_id_1 INTEGER,
        brand_id_2 INTEGER,
        brand_name_1 TEXT,
        brand_name_2 TEXT,
        rank_1 INTEGER,
        rank_2 INTEGER,
        rank_distance INTEGER,
        query_id INTEGER,
        provider_name TEXT,
        model_name TEXT,
        timestamp REAL,
        FOREIGN KEY (response_id) REFERENCES responses (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS competitor_relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id_1 INTEGER,
        brand_id_2 INTEGER,
        brand_name_1 TEXT,
        brand_name_2 TEXT,
        co_mention_count INTEGER,
        avg_rank_distance REAL,
        first_seen REAL,
        last_seen REAL,
        strength_score REAL,
        PRIMARY KEY (brand_id_1, brand_id_2)
    ) WITHOUT ROWID''')

    conn.commit()


async def main(with_sources=False):
    """
    Run LLM SEO analysis
    
    Args:
        with_sources: If True, use providers that request sources and confidence scores
    """
    config = load_config()
    BRANDS = config["brands"]
    QUERIES = config["queries"]
    PROVIDERS = get_providers(with_sources=with_sources)
    
    conn = sqlite3.connect("llmseo.db")
    c = conn.cursor()

    create_tables(conn)

    run_started = time.time()
    run_id = None
    success_count = 0
    error_count = 0
    total_operations = len(PROVIDERS) * len(QUERIES)

    c.execute('''INSERT INTO runs (started_at, total_queries, total_providers, success_count, error_count, with_sources)
                 VALUES (?, ?, ?, 0, 0, ?)''',
              (run_started, len(QUERIES), len(PROVIDERS), with_sources))
    run_id = c.lastrowid

    mode_str = "WITH SOURCES" if with_sources else "STANDARD"
    print(f"Starting LLM SEO analysis ({mode_str} mode) with {len(PROVIDERS)} providers and {len(QUERIES)} queries...")

    for provider_idx, provider in enumerate(PROVIDERS):
        print(f"\nProvider {provider_idx + 1}/{len(PROVIDERS)}: {provider.name} ({provider.model})")

        for query_idx, q in enumerate(QUERIES):
            print(f"  Query {query_idx + 1}/{len(QUERIES)}: {q['text'][:50]}...")

            try:
                res = await provider.rank(q["text"], q["k"])
                answers = res.get("answers", [])
                raw = json.dumps(res)
                
                current_timestamp = time.time()
                
                c.execute('''INSERT INTO responses (query_id, provider_name, model_name, raw_response, timestamp)
                            VALUES (?, ?, ?, ?, ?)''',
                          (q["id"], provider.name, getattr(provider, 'model', 'unknown'),
                           raw, current_timestamp))
                response_id = c.lastrowid
                
                mentions_found = 0
                mentioned_brands = []  # Track brands mentioned in this response
                
                for idx, a in enumerate(answers):
                    answer_name = a.get("name", "")
                    answer_why = a.get("why", "")
                    answer_sources = a.get("sources", [])
                    answer_confidence = a.get("confidence", None)

                    for brand in BRANDS:
                        alias = match_brand(answer_name, brand)
                        if alias:
                            mentions_found += 1
                            rank_position = idx + 1
                            
                            # Track for co-mention analysis
                            mentioned_brands.append((brand["id"], brand["name"], rank_position))
                            
                            # Insert mention
                            c.execute('''INSERT INTO mentions 
                                        (response_id, brand_id, brand_name, alias_used, rank_position, explanation, timestamp)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                      (response_id, brand["id"], brand["name"], alias,
                                       rank_position, answer_why, current_timestamp))
                            mention_id = c.lastrowid
                            
                            # Insert sources if available
                            if with_sources and answer_sources:
                                for source in answer_sources:
                                    c.execute('''INSERT INTO sources
                                                (mention_id, url, title, description, timestamp)
                                                VALUES (?, ?, ?, ?, ?)''',
                                             (mention_id, source.get("url", ""),
                                              source.get("title"), source.get("description"),
                                              current_timestamp))
                                
                                print(f"    ✓ Found {brand['name']} at rank #{rank_position} "
                                      f"(confidence: {answer_confidence:.2f}, sources: {len(answer_sources)})")
                            else:
                                print(f"    ✓ Found {brand['name']} at rank #{rank_position}")
                
                # Extract co-mentions for this response
                if len(mentioned_brands) >= 2:
                    co_mention_count = extract_co_mentions_for_response(
                        conn, response_id, mentioned_brands,
                        q["id"], provider.name, getattr(provider, 'model', 'unknown'),
                        current_timestamp
                    )
                    if co_mention_count > 0:
                        print(f"    → Tracked {co_mention_count} co-mention relationship(s)")

                if mentions_found == 0:
                    print(f"    No brand mentions found in top {q['k']} results")

                success_count += 1

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                print(f"    ✗ Error: {error_msg}")
                c.execute('''INSERT INTO responses (query_id, provider_name, model_name, timestamp, error_message)
                            VALUES (?, ?, ?, ?, ?)''',
                          (q["id"], provider.name, getattr(provider, 'model', 'unknown'),
                           time.time(), error_msg))

    run_completed = time.time()
    c.execute('''UPDATE runs SET completed_at = ?, success_count = ?, error_count = ?
                 WHERE id = ?''',
              (run_completed, success_count, error_count, run_id))

    conn.commit()
    conn.close()

    duration = run_completed - run_started
    print(f"\n{'='*60}")
    print(f"Analysis Complete ({mode_str} mode)")
    print(f"{'='*60}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Success: {success_count}/{total_operations}")
    print(f"Errors: {error_count}/{total_operations}")
    print(f"Database: llmseo.db")
    
    # Check if co-mentions were tracked
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM co_mentions')
    co_mention_count = c.fetchone()[0]
    if co_mention_count > 0:
        print(f"\nCompetitor Graph: {co_mention_count} co-mention relationships tracked")
    
    if with_sources:
        print(f"\nNext steps:")
        print(f"  1. Run hallucination analysis:")
        print(f"     python foundamental.py hallucination --analyze --verify-urls")
        print(f"  2. View hallucination report:")
        print(f"     python foundamental.py hallucination --report")
        print(f"  3. View competitor graph:")
        print(f"     python foundamental.py analyze --graph")
    else:
        print(f"\nNext steps:")
        print(f"  1. View analysis results:")
        print(f"     python foundamental.py analyze --report")
        print(f"  2. View competitor graph:")
        print(f"     python foundamental.py analyze --graph")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run LLM SEO Analysis')
    parser.add_argument('--with-sources', action='store_true',
                       help='Enable hallucination filter (request sources and confidence)')
    
    args = parser.parse_args()
    
    asyncio.run(main(with_sources=args.with_sources))
