# LLM-as-a-Judge Evaluation Architecture

## Overview

This document describes the LLM-as-a-Judge evaluation system, which replaces brittle regex-based evaluation with semantic understanding powered by cheap LLM models.

## Problem Statement

The original evaluation approach used exact string matching and regex patterns:

```python
def match_brand(name: str, brand):
    target = name.lower()
    if brand["name"].lower() == target:
        return brand["name"]
    for alias in brand["aliases"]:
        if alias.lower() == target:
            return alias
    return None
```

This approach fails for:
- **Partial matches**: "OpenAI's GPT-4" won't match "OpenAI"
- **Contextual references**: "The ChatGPT makers" won't match "OpenAI"  
- **Typos**: "Opan AI" won't match "OpenAI"
- **Variations**: "OpenAI Inc." or "OpenAI, Inc" won't match

## Solution: LLM-as-a-Judge

Use a small, cheap LLM to semantically evaluate matches. The LLM understands:
- Partial mentions and possessives
- Product-to-company relationships
- Contextual clues
- Common variations and abbreviations

### Cost Comparison

| Model | Cost per 1M tokens | Use Case |
|-------|-------------------|----------|
| GPT-5 nano | Very cheap | Default evaluator |
| GPT-3.5-turbo | ~$0.50 input / $1.50 output | Fallback |
| Ollama (local) | Free | Local development |

For typical evaluation workloads (100 evals/run, ~200 tokens each):
- **GPT-5 nano**: Very cheap per run
- **Ollama**: Free (but requires local setup)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Evaluator                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Brand Match │    │ Output Eval │    │ Batch Match │     │
│  │   (Single)  │    │  (Compare)  │    │  (Multiple) │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                    ┌───────┴───────┐                        │
│                    │  BAML Client  │                        │
│                    └───────┬───────┘                        │
│                            │                                │
│         ┌──────────────────┼──────────────────┐            │
│         │                  │                  │            │
│  ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐      │
│  │  GPT-5 nano │   │    Ollama   │   │   (Other)   │      │
│  │   (OpenAI)  │   │   (Local)   │   │             │      │
│  └─────────────┘   └─────────────┘   └─────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Brand Matching

```python
from llm_evaluator import LLMEvaluator, EvaluationConfig, EvaluatorBackend

evaluator = LLMEvaluator(EvaluationConfig(
    backend=EvaluatorBackend.OPENAI,  # or OLLAMA
    confidence_threshold=0.7,
    fallback_to_regex=True
))

# Match a brand in text
result = await evaluator.match_brand(
    text="OpenAI's latest GPT-4 model",
    brand_name="OpenAI",
    brand_aliases=["ChatGPT", "GPT"]
)

print(result.is_match)      # True
print(result.confidence)    # 0.95
print(result.reasoning)     # "The text explicitly mentions 'OpenAI's'..."
```

### Quick Functions

```python
from llm_evaluator import llm_match_brand, llm_eval

# Quick brand check
is_match = await llm_match_brand("ChatGPT is popular", "OpenAI", ["ChatGPT"])

# Quick output evaluation
passed = await llm_eval(
    expected="OpenAI is a leading AI company",
    actual="OpenAI leads in AI research",
    criteria="semantic similarity"
)
```

### Batch Matching

```python
# Match multiple brands efficiently
brands = [
    {"name": "OpenAI", "aliases": ["ChatGPT"]},
    {"name": "Anthropic", "aliases": ["Claude"]},
    {"name": "Pinecone", "aliases": []},
]

results = await evaluator.match_brands_batch(
    text="OpenAI and Anthropic are leading AI companies",
    brands=brands
)
```

### Environment Variables

```bash
# Enable LLM matching in run.py
USE_LLM_MATCHING=true

# Choose backend (openai or ollama)
LLM_EVAL_BACKEND=openai

# Confidence threshold (0.0 to 1.0)
LLM_EVAL_THRESHOLD=0.7
```

## BAML Functions

The evaluator uses these BAML functions:

### EvalBrandMatch
```baml
function EvalBrandMatch(text: string, brand_name: string, brand_aliases: string[]) -> BrandMatchResult
```

### EvalBrandMatchBatch  
```baml
function EvalBrandMatchBatch(text: string, brands: string[]) -> BrandMatchBatchResult
```

### EvalOutput
```baml
function EvalOutput(expected: string, actual: string, criteria: string) -> EvalResult
```

## Response Types

```python
class BrandMatchResult:
    is_match: bool
    confidence: float  # 0.0 to 1.0
    matched_alias: Optional[str]
    reasoning: str

class EvalResult:
    passed: bool
    score: float  # 0.0 to 1.0
    feedback: str
    issues: List[str]
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backend` | EvaluatorBackend | OPENAI | Which LLM to use |
| `confidence_threshold` | float | 0.7 | Minimum confidence for match |
| `fallback_to_regex` | bool | True | Use regex if LLM fails |
| `cache_results` | bool | True | Cache eval results |

## Testing

Run the LLM evaluator tests:

```bash
# Run dedicated evaluator tests
python tests/test_llm_evaluator.py

# Run full test suite (includes evaluator tests)
python tests/test_suite.py
```

## Best Practices

1. **Use caching**: Enable `cache_results=True` to avoid redundant API calls
2. **Batch when possible**: Use `match_brands_batch` for multiple brands
3. **Set appropriate thresholds**: 0.7 is a good default, increase for stricter matching
4. **Enable fallback**: Keep `fallback_to_regex=True` for reliability
5. **Use Ollama for development**: Free and fast for local testing

## Migration from Regex

To migrate from regex to LLM matching:

1. Set `USE_LLM_MATCHING=true` in environment
2. Run tests to verify accuracy
3. Gradually increase confidence threshold if seeing false positives
4. Monitor API costs (should be minimal)

The system maintains backward compatibility - set `USE_LLM_MATCHING=false` to use regex.

## UI Integration

The LLM-as-a-Judge system is fully integrated with the web UI dashboard.

### Dashboard Features

The main dashboard (`/`) displays:
- **LLM vs Regex Match Counts**: Shows how many brand matches used LLM vs regex
- **Average Match Confidence**: Overall confidence score for LLM-matched brands
- **Match Method Column**: Each mention shows whether it was matched via 🤖 LLM or 📝 Regex
- **Confidence Scores**: Hover over LLM matches to see the reasoning

### Database Schema

The `mentions` table includes LLM evaluation metadata:

```sql
CREATE TABLE mentions (
    ...
    match_method TEXT DEFAULT 'regex',    -- 'llm' or 'regex'
    match_confidence REAL,                 -- 0.0 to 1.0
    match_reasoning TEXT                   -- LLM's explanation
);
```

Evaluation statistics are tracked per run:

```sql
CREATE TABLE evaluation_stats (
    id INTEGER PRIMARY KEY,
    run_id INTEGER,
    eval_method TEXT,
    total_evaluations INTEGER,
    avg_confidence REAL,
    high_confidence_count INTEGER,
    low_confidence_count INTEGER,
    fallback_count INTEGER,
    timestamp REAL
);
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/stats` | Dashboard stats including LLM/regex counts |
| `GET /api/mentions` | Mentions with match_method, confidence, reasoning |
| `GET /api/evaluation-stats` | Historical LLM evaluation statistics |
| `GET /api/confidence-distribution` | Confidence score distribution |

### Running with LLM Matching

```bash
# Enable LLM matching and run analysis
USE_LLM_MATCHING=true python src/run.py

# Start the UI to view results
cd ui && cargo run
```

Open http://localhost:8000 to view the dashboard with LLM evaluation insights.
