use serde::{Deserialize, Serialize};

/// Brand mention from an LLM response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrandMention {
    pub id: i64,
    pub brand_id: i64,
    pub brand_name: String,
    pub alias_used: String,
    pub rank_position: i32,
    pub explanation: Option<String>,
    pub response_id: i64,
}

/// LLM Provider response record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Response {
    pub id: i64,
    pub provider_name: String,
    pub model_name: String,
    pub query_id: Option<i64>,
    pub raw_response: Option<String>,
    pub timestamp: f64,
    pub error_message: Option<String>,
}

/// Brand configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Brand {
    pub id: i64,
    pub name: String,
    pub aliases: Vec<String>,
}

/// Query configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Query {
    pub id: i64,
    pub text: String,
    pub k: i32,
    pub category: String,
}

/// Brand ranking data for reports
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrandRanking {
    pub brand_name: String,
    pub provider: String,
    pub model: String,
    pub query: String,
    pub rank: i32,
    pub alias_used: String,
    pub explanation: Option<String>,
}

/// Provider performance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderPerformance {
    pub provider: String,
    pub model: String,
    pub total_mentions: i32,
    pub avg_rank: Option<f64>,
    pub total_responses: i32,
    pub successful_responses: i32,
    pub success_rate: f64,
}

/// Co-mention relationship between brands
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoMention {
    pub id: i64,
    pub response_id: i64,
    pub brand_name_1: String,
    pub brand_name_2: String,
    pub rank_1: i32,
    pub rank_2: i32,
    pub rank_distance: i32,
    pub provider_name: String,
    pub model_name: String,
    pub timestamp: f64,
}

/// Competitor relationship (aggregated co-mentions)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompetitorRelationship {
    pub brand_name_1: String,
    pub brand_name_2: String,
    pub co_mention_count: i32,
    pub avg_rank_distance: f64,
    pub strength_score: f64,
    pub first_seen: f64,
    pub last_seen: f64,
}

/// Graph node for visualization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub size: Option<f64>,
}

/// Graph edge for visualization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphEdge {
    pub source: String,
    pub target: String,
    pub weight: f64,
    pub co_mentions: i32,
    pub avg_distance: f64,
}

/// Complete graph data for visualization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompetitorGraph {
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
    pub total_nodes: usize,
    pub total_edges: usize,
}

/// Source/citation from LLM response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Source {
    pub id: i64,
    pub mention_id: i64,
    pub url: Option<String>,
    pub title: Option<String>,
    pub description: Option<String>,
    pub is_valid: bool,
    pub is_accessible: bool,
    pub status_code: Option<i32>,
    pub validation_error: Option<String>,
}

/// Hallucination risk score for a mention
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HallucinationScore {
    pub id: i64,
    pub mention_id: i64,
    pub brand_name: String,
    pub confidence_score: f64,
    pub reliability_score: f64,
    pub risk_level: String,
    pub has_source: bool,
    pub source_accessible: bool,
    pub source_count: i32,
}

/// Response quality metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseQuality {
    pub response_id: i64,
    pub provider_name: String,
    pub model_name: String,
    pub avg_reliability: f64,
    pub high_risk_count: i32,
    pub medium_risk_count: i32,
    pub low_risk_count: i32,
    pub total_mentions: i32,
    pub overall_quality: String,
}

/// Dashboard summary statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardStats {
    pub total_brands: i32,
    pub total_responses: i32,
    pub total_mentions: i32,
    pub total_co_mentions: i32,
    pub avg_reliability: f64,
    pub high_risk_count: i32,
    pub medium_risk_count: i32,
    pub low_risk_count: i32,
}

/// Temporal graph snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemporalSnapshot {
    pub window_start: String,
    pub window_end: String,
    pub edges: Vec<GraphEdge>,
    pub edge_count: usize,
}
