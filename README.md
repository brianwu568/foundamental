# Foundamental - Brand Visibility Tracker in LLMs

A Python application that helps brands understand their visibility and ranking across different Large Language Models (LLMs). Track how your brand appears in LLM responses compared to competitors.

**Built with BAML** - Uses structured prompting and type-safe LLM interactions via BAML templates.

## Features

- **Multi-Provider Support**: Query multiple LLM providers (OpenAI, Ollama, etc.)
- **BAML Integration**: Type-safe, templated prompts with structured outputs
- **Brand Tracking**: Monitor mentions of your brand and competitors
- **Ranking Analysis**: See where brands rank in LLM responses
- **Sentiment Analysis**: Analyze sentiment of brand mentions
- **Competitor Graph**: Track co-mention networks and competitive relationships over time
- **Hallucination Filter**: Request sources/citations and score confidence to detect hallucinations
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
# Standard analysis
python foundamental.py run

# With hallucination filter (requests sources and confidence)
python foundamental.py run --with-sources
```

### View Results
```bash
python foundamental.py analyze --report
```

### Compare Providers
```bash
python foundamental.py analyze --compare
```

### Analyze Brand Sentiment
```bash
python foundamental.py sentiment --analyze
python foundamental.py sentiment --report
```

### Hallucination Filter
```bash
# Analyze hallucination risks
python foundamental.py hallucination --analyze --verify-urls

# View hallucination report
python foundamental.py hallucination --report
```

### Competitor Graph Analysis
```bash
# View competitor co-mention network
python foundamental.py analyze --graph

# Focus on specific brand's competitors
python foundamental.py analyze --graph --brand YourBrand

# Export graph to JSON for visualization
python foundamental.py analyze --export-graph competitor_graph.json

# Export to NetworkX (graph analysis)
python src/competitor_graph.py --export-networkx graph.gpickle

# Export to PyTorch Geometric (graph neural networks)
python src/competitor_graph.py --export-pyg graph.pt

# Export as adjacency matrix (NumPy/Pandas)
python src/competitor_graph.py --export-adjacency matrix.csv

# Filter by relationship strength
python foundamental.py analyze --export-graph graph.json --min-strength 0.5
```

The competitor graph automatically tracks when brands are mentioned together in LLM responses, building a co-mention network over time. This helps you understand:
- Which brands are considered direct competitors by LLMs
- How competitive relationships evolve over time
- The strength of competitive associations based on co-mention frequency and rank proximity

**Export Formats:** JSON, NetworkX, PyTorch Geometric (PyG), Adjacency Matrix (NumPy/CSV)  

### Export Results
```bash
python foundamental.py analyze --export results.json
```

## Output

The application creates a SQLite database (`llmseo.db`) with several main tables:

- **responses**: Raw LLM responses
- **mentions**: Brand mentions and rankings  
- **runs**: Execution metadata
- **co_mentions**: Co-occurrence relationships between brands
- **competitor_relationships**: Aggregated competitive relationships over time
- **sources**: URLs and citations from LLM responses (when using --with-sources)
- **hallucination_scores**: Reliability scores for detecting hallucinations

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

## Adding Other Model Providers/Methods of Analysis

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
- Ollama running locally (for Ollama provider) on port `11434`

## Database Schema

- `responses`: Stores raw LLM responses and metadata
- `mentions`: Tracks brand mentions with ranking positions
- `runs`: Execution history and statistics

## License

This project is available for usage under the [MIT License](https://opensource.org/license/mit).

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
- [x] Hallucination Filter: Ask models to output URLs/sources and score confidence
- [x] Competitor graph (co-mention network over time)
- [ ] LLM-as-a-judge: Swap out Regular Expressions for a small, cheap model to do evals
- [ ] Attribution tests
- [ ] Simple UI
