# Competitor Graph Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER RUNS NORMAL QUERY                          │
│                   python foundamental.py run                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         QUERY EXECUTION LOOP                            │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  For each Provider (OpenAI, Ollama, etc.)                      │    │
│  │    For each Query (from config.json)                           │    │
│  │      1. Call LLM with ranking prompt                           │    │
│  │      2. Get structured response (BAML)                         │    │
│  │      3. Store response in DB                                   │    │
│  └────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BRAND MENTION DETECTION                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  For each Answer in Response:                                  │    │
│  │    • Match against configured brands                           │    │
│  │    • Record: brand_id, rank_position, explanation              │    │
│  │    • Store in mentions table                                   │    │
│  │    • Track in mentioned_brands list                            │    │
│  └────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 AUTOMATIC CO-MENTION EXTRACTION                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  IF len(mentioned_brands) >= 2:                                │    │
│  │    For each brand pair (i, j):                                 │    │
│  │      • Create co-mention record                                │    │
│  │      • Calculate rank_distance = |rank_i - rank_j|             │    │
│  │      • Store: brands, ranks, query, provider, timestamp        │    │
│  │    Print: "→ Tracked N co-mention relationship(s)"             │    │
│  └────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATABASE STORAGE                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  responses   │  │   mentions   │  │ co_mentions                  │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────────────┤  │
│  │ query_id     │  │ response_id  │  │ response_id                  │  │
│  │ provider     │  │ brand_id     │  │ brand_id_1, brand_id_2       │  │
│  │ model        │  │ rank_position│  │ rank_1, rank_2               │  │
│  │ raw_response │  │ explanation  │  │ rank_distance                │  │
│  │ timestamp    │  │ timestamp    │  │ query_id, provider, model    │  │
│  └──────────────┘  └──────────────┘  │ timestamp                    │  │
│                                       └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

                          Data Accumulates Over Time

┌─────────────────────────────────────────────────────────────────────────┐
│                    USER REQUESTS ANALYSIS                               │
│             python foundamental.py analyze --graph                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  COMPETITOR GRAPH ANALYZER                              │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  1. Extract co-mentions from DB                                │    │
│  │     • Query co_mentions table                                  │    │
│  │     • Group by brand pairs                                     │    │
│  │                                                                 │    │
│  │  2. Calculate aggregated metrics                               │    │
│  │     • co_mention_count = total occurrences                     │    │
│  │     • avg_rank_distance = average proximity                    │    │
│  │     • first_seen, last_seen = temporal bounds                  │    │
│  │                                                                 │    │
│  │  3. Calculate strength scores                                  │    │
│  │     frequency_factor = min(count / 10, 1.0)                    │    │
│  │     proximity_factor = 1 - (avg_distance / max_distance)       │    │
│  │     strength = (frequency × 0.6) + (proximity × 0.4)           │    │
│  │                                                                 │    │
│  │  4. Store in competitor_relationships table                    │    │
│  └────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT GENERATION                               │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Option 1: Console Report                                      │    │
│  │    • Network statistics                                        │    │
│  │    • Strongest relationships                                   │    │
│  │    • Brand-specific competitors (if --brand flag)              │    │
│  │    • Temporal evolution                                        │    │
│  │                                                                 │    │
│  │  Option 2: JSON Export (if --export-graph)                     │    │
│  │    {                                                            │    │
│  │      "nodes": [...],                                           │    │
│  │      "edges": [...],                                           │    │
│  │      "temporal_evolution": [...]                               │    │
│  │    }                                                            │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                        DATA FLOW VISUALIZATION
═══════════════════════════════════════════════════════════════════════════

Query: "Best AI platforms"
Response: ["OpenAI", "YourBrand", "Anthropic", "CompetitorX", "Google"]

  Step 1: Brand Detection
  ┌────────────────────────────────────────────────────┐
  │  Rank 1: OpenAI        → brand_id=3, rank=1        │
  │  Rank 2: YourBrand     → brand_id=1, rank=2        │
  │  Rank 3: Anthropic     → (not in config, skip)     │
  │  Rank 4: CompetitorX   → brand_id=2, rank=4        │
  │  Rank 5: Google        → (not in config, skip)     │
  │                                                     │
  │  mentioned_brands = [(3, OpenAI, 1),               │
  │                      (1, YourBrand, 2),            │
  │                      (2, CompetitorX, 4)]          │
  └────────────────────────────────────────────────────┘

  Step 2: Co-mention Extraction
  ┌────────────────────────────────────────────────────┐
  │  Pair 1: OpenAI (1) ↔ YourBrand (2)                │
  │    → rank_distance = |1 - 2| = 1                   │
  │                                                     │
  │  Pair 2: OpenAI (1) ↔ CompetitorX (4)              │
  │    → rank_distance = |1 - 4| = 3                   │
  │                                                     │
  │  Pair 3: YourBrand (2) ↔ CompetitorX (4)           │
  │    → rank_distance = |2 - 4| = 2                   │
  │                                                     │
  │  Result: 3 co-mentions tracked ✓                   │
  └────────────────────────────────────────────────────┘

  Step 3: Over Time (10 queries later...)
  ┌────────────────────────────────────────────────────┐
  │  YourBrand ↔ CompetitorX:                          │
  │    co_mention_count = 8                            │
  │    avg_rank_distance = 2.3                         │
  │    strength_score = 0.72                           │
  │    → "Strong competitor relationship"              │
  └────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                      INTEGRATION POINTS
═══════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────┐
│  Feature: Hallucination Filter                                         │
│  Integration: Co-mentions with verified sources are more reliable      │
│                                                                         │
│  Example:                                                               │
│    YourBrand ↔ CompetitorX (8 co-mentions)                             │
│    • 6 with sources (75%)                                               │
│    • 4 sources verified accessible (50%)                                │
│    → High confidence competitive relationship                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Feature: Sentiment Analysis                                           │
│  Integration: Analyze sentiment when brands co-occur                   │
│                                                                         │
│  Example:                                                               │
│    YourBrand ↔ CompetitorX co-mentions                                 │
│    • When mentioned together, YourBrand sentiment: +0.65                │
│    • When mentioned together, CompetitorX sentiment: +0.58              │
│    → Slight sentiment advantage when compared                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Feature: Multi-Provider Analysis                                      │
│  Integration: Different LLMs may perceive different competitors        │
│                                                                         │
│  Example:                                                               │
│    OpenAI:  YourBrand ↔ CompetitorX (strength: 0.82)                   │
│    Ollama:  YourBrand ↔ CompetitorY (strength: 0.75)                   │
│    → Different models have different competitive perceptions            │
└─────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                        STRENGTH SCORE BREAKDOWN
═══════════════════════════════════════════════════════════════════════════

Example: YourBrand ↔ CompetitorX
  • Co-mentions: 18
  • Avg rank distance: 2.1

Calculation:
  ┌──────────────────────────────────────────────────┐
  │  Frequency Factor (60% weight):                  │
  │    count_normalized = min(18 / 10, 1.0) = 1.0    │
  │    frequency_score = 1.0 × 0.6 = 0.60            │
  │                                                   │
  │  Proximity Factor (40% weight):                  │
  │    proximity = 1 - (2.1 / 10) = 0.79             │
  │    proximity_score = 0.79 × 0.4 = 0.316          │
  │                                                   │
  │  Total Strength Score:                           │
  │    0.60 + 0.316 = 0.916                          │
  │                                                   │
  │  Interpretation: Very strong competitor          │
  └──────────────────────────────────────────────────┘

Strength Scale:
  0.7 - 1.0  ████████████████████ Strong/Direct Competitor
  0.4 - 0.7  ███████████░░░░░░░░░ Moderate Competitor
  0.0 - 0.4  ████░░░░░░░░░░░░░░░░ Weak/Peripheral
```
