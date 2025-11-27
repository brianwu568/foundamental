class Answer {
  name string
  why string
}

class RankingResult {
  answers Answer[]
}

// Hallucination Filter: Source citation class
class Source {
  url string
  title string?
  description string?
}

// Hallucination Filter: Answer with sources and confidence
class AnswerWithSources {
  name string
  why string
  sources Source[]
  confidence float @description("Confidence score from 0.0 to 1.0")
}

class RankingResultWithSources {
  answers AnswerWithSources[]
}

enum Sentiment {
  Positive
  Neutral
  Negative
}

class SentimentResult {
  sentiment Sentiment
  confidence float
}

function RankEntities(query: string, k: int) -> RankingResult {
  client "openai/gpt-4o-mini"

  prompt #"
    You are a rankings engine. Given a user query, return the top-K entities
    that best answer the query. Return STRICT JSON that conforms to the
    output schema.

    Query: {{ query }}
    TopK: {{ k }}

    {{ ctx.output_format }}
  "#
}

function RankEntitiesOpenAI(query: string, k: int) -> RankingResult {
  client CustomGPT4oMini

  prompt #"
    You are a rankings engine. Given a user query, return the top-K entities
    that best answer the query. Return STRICT JSON that conforms to the
    output schema.

    Query: {{ query }}
    TopK: {{ k }}

    {{ ctx.output_format }}
  "#
}

function RankEntitiesOllama(query: string, k: int) -> RankingResult {
  client OllamaLocal

  prompt #"
    You are a rankings engine. Given a user query, return the top-K entities
    that best answer the query. Return STRICT JSON that conforms to the
    output schema.

    Query: {{ query }}
    TopK: {{ k }}

    {{ ctx.output_format }}
  "#
}

function BrandSentiment(brand: string, passage: string) -> SentimentResult {
  client "openai/gpt-4o-mini"

  prompt #"
    Classify sentiment toward the brand in the passage.
    Return STRICT JSON matching the schema.

    Brand: {{ brand }}
    Passage:
    {{ passage }}

    {{ ctx.output_format }}
  "#
}

// Hallucination Filter: OpenAI ranking with sources and confidence
function RankEntitiesWithSourcesOpenAI(query: string, k: int) -> RankingResultWithSources {
  client CustomGPT4oMini

  prompt #"
    You are a rankings engine with source attribution capabilities.
    
    Given a user query, return the top-K entities that best answer the query.
    
    IMPORTANT REQUIREMENTS:
    1. For EACH entity, provide at least 1-3 credible source URLs that support why this entity is relevant
    2. Include a confidence score (0.0 to 1.0) indicating how confident you are in this ranking
    3. Only include entities you can support with real, verifiable sources
    4. DO NOT make up URLs - if you cannot find a credible source, use a lower confidence score
    
    Return STRICT JSON that conforms to the output schema.

    Query: {{ query }}
    TopK: {{ k }}

    {{ ctx.output_format }}
  "#
}

// Hallucination Filter: Ollama ranking with sources and confidence
function RankEntitiesWithSourcesOllama(query: string, k: int) -> RankingResultWithSources {
  client OllamaLocal

  prompt #"
    You are a rankings engine with source attribution capabilities.
    
    Given a user query, return the top-K entities that best answer the query.
    
    IMPORTANT REQUIREMENTS:
    1. For EACH entity, provide at least 1-3 credible source URLs that support why this entity is relevant
    2. Include a confidence score (0.0 to 1.0) indicating how confident you are in this ranking
    3. Only include entities you can support with real, verifiable sources
    4. DO NOT make up URLs - if you cannot find a credible source, use a lower confidence score
    
    Return STRICT JSON that conforms to the output schema.

    Query: {{ query }}
    TopK: {{ k }}

    {{ ctx.output_format }}
  "#
}

test sample_rank {
  functions [RankEntities]
  args {
    query "best LLM providers"
    k 3
  }
}

test sample_sentiment {
  functions [BrandSentiment]
  args {
    brand "AcmeCo"
    passage #"
      People love AcmeCo's support, but the app is buggy.
    "#
  }
}
