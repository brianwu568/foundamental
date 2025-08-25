# Foundamental - Brand Visibility Tracker

A Python application that helps brands understand their visibility and ranking across different Large Language Models (LLMs). Track how your brand appears in LLM responses compared to competitors.

**Built with BAML** - Uses structured prompting and type-safe LLM interactions via BAML templates.

## Features

- **Multi-Provider Support**: Query multiple LLM providers (OpenAI, Ollama, etc.)
- **BAML Integration**: Type-safe, templated prompts with structured outputs
- **Brand Tracking**: Monitor mentions of your brand and competitors
- **Ranking Analysis**: See where brands rank in LLM responses
- **Sentiment Analysis**: Analyze sentiment of brand mentions
- **SQLite Storage**: Persistent storage of all results
- **Comprehensive Analytics**: Detailed reports and comparisons
- **Configurable**: Easy configuration via JSON files

## Installation

1. **Clone and setup:**
```bash
git clone <repository-url>
cd foundamental
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Setup environment:**
```bash
cp .env.example .env
```

4. **Configure your analysis:**
Edit `config.json` to add your brands and queries.

## Configuration

### Brands Setup (`config.json`)
For each bramd that you want to test, set up an object in `config.json` as follows:
```json
{
  "brands": [
    {
      "id": 1,
      "name": "YourBrand", 
      "aliases": ["Your Brand", "YB", "YourBrand.com"]
    }
  ]
}
```

### Queries Setup
Define the queries you want to test:
```json
{
  "queries": [
    {
      "id": 1,
      "text": "Best vector database for RAG",
      "k": 5,
      "category": "technical"
    }
  ]
}
```

## Usage

### Run Analysis
```bash
python llmseo.py run
```

### View Results
```bash
python llmseo.py analyze --report
```

### Compare Providers
```bash
python llmseo.py analyze --compare
```

### Analyze Brand Sentiment
```bash
python llmseo.py sentiment --analyze
python llmseo.py sentiment --report
```

### Export Results
```bash
python llmseo.py analyze --export results.json
```

## Output

The application creates a SQLite database (`llmseo.db`) with three main tables:

- **responses**: Raw LLM responses
- **mentions**: Brand mentions and rankings  
- **runs**: Execution metadata

## Example Output

```
LLM SEO Brand Visibility Report
==================================================

YourBrand
------------

  OPENAI (gpt-4o-mini)
    Query: Best vector database for RAG
      #3 - YourBrand
           Leading solution for enterprise RAG implementations...

Provider Performance Comparison
========================================
Provider        Model           Mentions   Avg Rank   Success Rate
----------------------------------------------------------------------
openai          gpt-4o-mini     2          2.5        100.0%
ollama          llama3          1          4.0        100.0%
```

## Extending the Application

### Add New Providers
1. Create a new provider class in `src/providers/`
2. Inherit from `LLMProvider` base class
3. Implement the `rank()` method
4. Add to `PROVIDERS` list in `run.py`

### Custom Analysis
The SQLite database can be queried directly for custom analysis:
```sql
SELECT brand_name, AVG(rank_position) as avg_rank 
FROM mentions 
GROUP BY brand_name;
```

## Requirements

- Python 3.7+
- OpenAI API key (for OpenAI provider)
- Ollama running locally (for Ollama provider)

## Database Schema

- `responses`: Stores raw LLM responses and metadata
- `mentions`: Tracks brand mentions with ranking positions
- `runs`: Execution history and statistics

## License

TODO

## BAML Integration

This application uses BAML for structured LLM interactions. The prompts are defined in `baml_src/llm_seo.baml`:

- **RankEntitiesOpenAI**: OpenAI-specific ranking function
- **RankEntitiesOllama**: Ollama-specific ranking function  
- **BrandSentiment**: Sentiment analysis for brand mentions

The BAML client is pre-generated in `baml_client/`. If you modify the BAML files, regenerate by running the following in the root directory.
```bash
baml-cli generate
```

## Roadmap
- [ ] LLM-as-a-judge: Swap out Regular Expressions for a small, cheap model to do evals
- [ ] Hallucination Filter: Ask models to output URLs/sources and score confidence
- [ ] Competitor graph (co-mention network over time)
- [ ] Attribution tests
- [ ] Simple UI
