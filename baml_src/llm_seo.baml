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

// ============================================================================
// LLM-as-a-Judge Evaluation Functions
// ============================================================================

// Result of brand matching evaluation
class BrandMatchResult {
  is_match bool @description("Whether the text refers to the target brand")
  confidence float @description("Confidence score from 0.0 to 1.0")
  matched_alias string? @description("The specific alias or variation that was matched, if any")
  reasoning string @description("Brief explanation of why this is or isn't a match")
}

// Result of evaluating multiple brands against a text
class BrandMatchBatchResult {
  matches BrandMatch[]
}

class BrandMatch {
  brand_name string @description("The brand being evaluated")
  is_match bool
  confidence float
  matched_text string? @description("The specific text that matched the brand")
  reasoning string
}

// Evaluation result for comparing expected vs actual output
class EvalResult {
  passed bool @description("Whether the evaluation passed")
  score float @description("Score from 0.0 to 1.0")
  feedback string @description("Detailed feedback on the evaluation")
  issues string[] @description("List of specific issues found, if any")
}

// Function to check if a text mentions a specific brand (using cheap model)
function EvalBrandMatch(text: string, brand_name: string, brand_aliases: string[]) -> BrandMatchResult {
  client CustomGPT4oMini
  
  prompt #"
    You are an evaluation judge for brand mention detection.
    
    Determine if the given text refers to the target brand. Consider:
    - Exact name matches
    - Known aliases and variations
    - Partial matches (e.g., "OpenAI's product" mentions "OpenAI")
    - Common misspellings or abbreviations
    - Context clues that clearly indicate the brand
    
    Target Brand: {{ brand_name }}
    Known Aliases: {{ brand_aliases }}
    
    Text to evaluate:
    {{ text }}
    
    Return your evaluation as JSON matching the schema.
    Be generous with partial matches but confident about exact matches.
    
    {{ ctx.output_format }}
  "#
}

// Function to evaluate brand matches using Ollama (free local model)
function EvalBrandMatchOllama(text: string, brand_name: string, brand_aliases: string[]) -> BrandMatchResult {
  client OllamaLocal
  
  prompt #"
    You are an evaluation judge for brand mention detection.
    
    Determine if the given text refers to the target brand. Consider:
    - Exact name matches
    - Known aliases and variations
    - Partial matches (e.g., "OpenAI's product" mentions "OpenAI")
    - Common misspellings or abbreviations
    - Context clues that clearly indicate the brand
    
    Target Brand: {{ brand_name }}
    Known Aliases: {{ brand_aliases }}
    
    Text to evaluate:
    {{ text }}
    
    Return your evaluation as JSON matching the schema.
    Be generous with partial matches but confident about exact matches.
    
    {{ ctx.output_format }}
  "#
}

// Batch evaluation of multiple brands against a single text
function EvalBrandMatchBatch(text: string, brands: string[]) -> BrandMatchBatchResult {
  client CustomGPT4oMini
  
  prompt #"
    You are an evaluation judge for brand mention detection.
    
    Given a text, determine which of the provided brands are mentioned.
    Consider exact matches, partial matches, abbreviations, and context clues.
    
    Brands to check: {{ brands }}
    
    Text to evaluate:
    {{ text }}
    
    For each brand, provide:
    - Whether it's mentioned (is_match)
    - Confidence score (0.0 to 1.0)
    - The specific text that matched (if any)
    - Brief reasoning
    
    {{ ctx.output_format }}
  "#
}

// General evaluation function for comparing expected vs actual outputs
function EvalOutput(expected: string, actual: string, criteria: string) -> EvalResult {
  client CustomGPT4oMini
  
  prompt #"
    You are an evaluation judge comparing expected vs actual outputs.
    
    Evaluation Criteria: {{ criteria }}
    
    Expected Output:
    {{ expected }}
    
    Actual Output:
    {{ actual }}
    
    Evaluate how well the actual output matches the expected output based on the criteria.
    Consider semantic similarity, not just exact string matching.
    
    {{ ctx.output_format }}
  "#
}

// Evaluation function using Ollama for free local evaluation
function EvalOutputOllama(expected: string, actual: string, criteria: string) -> EvalResult {
  client OllamaLocal
  
  prompt #"
    You are an evaluation judge comparing expected vs actual outputs.
    
    Evaluation Criteria: {{ criteria }}
    
    Expected Output:
    {{ expected }}
    
    Actual Output:
    {{ actual }}
    
    Evaluate how well the actual output matches the expected output based on the criteria.
    Consider semantic similarity, not just exact string matching.
    
    {{ ctx.output_format }}
  "#
}
