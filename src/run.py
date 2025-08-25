# Import Required Packages
import re
import asyncio
import time
import json
import sqlite3
import os
from pathlib import Path
from .providers.openai_provider import OpenAIProvider
from .providers.ollama_provider import OllamaProvider

def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    if not os.path.exists(config_path):
        return {
            "brands": [
                {"id": 1, "name": "YourBrand", "aliases": ["Your Brand", "YB"]},
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
    OpenAIProvider(model="gpt-4o-mini"),
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
    
    c.execute('''INSERT INTO runs (started_at, total_queries, total_providers, success_count, error_count)
                 VALUES (?, ?, ?, 0, 0)''', 
              (run_started, len(QUERIES), len(PROVIDERS)))
    run_id = c.lastrowid
    
    print(f"Starting LLM SEO analysis with {len(PROVIDERS)} providers and {len(QUERIES)} queries...")
    
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
                        alias = match_brand(answer_name, brand)
                        if alias:
                            mentions_found += 1
                            c.execute('''INSERT INTO mentions 
                                        (response_id, brand_id, brand_name, alias_used, rank_position, explanation, timestamp)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                      (response_id, brand["id"], brand["name"], alias, 
                                       idx + 1, answer_why, time.time()))
                            
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
    
    conn.commit()
    conn.close()
    
    duration = run_completed - run_started
    print(f"\n🎯 Analysis Complete!")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Success: {success_count}/{total_operations}")
    print(f"   Errors: {error_count}/{total_operations}")
    print(f"   Database: llmseo.db")

if __name__ == "__main__":
    asyncio.run(main())