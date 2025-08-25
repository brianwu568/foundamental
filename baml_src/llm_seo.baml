class Answer {
  name string
  why string
}

class RankingResult {
  answers Answer[]
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
