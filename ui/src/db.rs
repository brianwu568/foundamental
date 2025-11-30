use rusqlite::{Connection, Result, params};
use std::collections::HashMap;
use std::path::Path;
use crate::models::*;

const DEFAULT_DB_PATH: &str = "../llmseo.db";

/// Get database connection
pub fn get_connection() -> Result<Connection> {
    let db_path = std::env::var("LLMSEO_DB_PATH")
        .unwrap_or_else(|_| DEFAULT_DB_PATH.to_string());
    
    // Check if database exists
    if !Path::new(&db_path).exists() {
        return Err(rusqlite::Error::QueryReturnedNoRows);
    }
    
    Connection::open(&db_path)
}

/// Get dashboard summary statistics
pub fn get_dashboard_stats() -> Result<DashboardStats> {
    let conn = get_connection()?;
    
    // Total brands (from mentions)
    let total_brands: i32 = conn.query_row(
        "SELECT COUNT(DISTINCT brand_name) FROM mentions",
        [],
        |row| row.get(0)
    ).unwrap_or(0);
    
    // Total responses
    let total_responses: i32 = conn.query_row(
        "SELECT COUNT(*) FROM responses WHERE error_message IS NULL",
        [],
        |row| row.get(0)
    ).unwrap_or(0);
    
    // Total mentions
    let total_mentions: i32 = conn.query_row(
        "SELECT COUNT(*) FROM mentions",
        [],
        |row| row.get(0)
    ).unwrap_or(0);
    
    // Total co-mentions
    let total_co_mentions: i32 = conn.query_row(
        "SELECT COUNT(*) FROM co_mentions",
        [],
        |row| row.get(0)
    ).unwrap_or(0);
    
    // Hallucination stats
    let (avg_reliability, high_risk, medium_risk, low_risk): (f64, i32, i32, i32) = conn.query_row(
        "SELECT 
            COALESCE(AVG(reliability_score), 0.0),
            COALESCE(SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END), 0)
         FROM hallucination_scores",
        [],
        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
    ).unwrap_or((0.0, 0, 0, 0));
    
    // LLM vs Regex match counts
    let (llm_match_count, regex_match_count, avg_match_confidence): (i32, i32, f64) = conn.query_row(
        "SELECT 
            COALESCE(SUM(CASE WHEN match_method = 'llm' THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN match_method = 'regex' OR match_method IS NULL THEN 1 ELSE 0 END), 0),
            COALESCE(AVG(match_confidence), 0.0)
         FROM mentions",
        [],
        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?))
    ).unwrap_or((0, 0, 0.0));
    
    Ok(DashboardStats {
        total_brands,
        total_responses,
        total_mentions,
        total_co_mentions,
        avg_reliability,
        high_risk_count: high_risk,
        medium_risk_count: medium_risk,
        low_risk_count: low_risk,
        llm_match_count,
        regex_match_count,
        avg_match_confidence,
    })
}

/// Get all brand rankings
pub fn get_brand_rankings() -> Result<Vec<BrandRanking>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            m.brand_name,
            r.provider_name,
            r.model_name,
            r.query_id,
            m.rank_position,
            m.alias_used,
            m.explanation
         FROM mentions m
         JOIN responses r ON m.response_id = r.id
         ORDER BY m.brand_name, r.provider_name, m.rank_position"
    )?;
    
    let rankings = stmt.query_map([], |row| {
        Ok(BrandRanking {
            brand_name: row.get(0)?,
            provider: row.get(1)?,
            model: row.get(2)?,
            query: format!("Query {}", row.get::<_, i64>(3).unwrap_or(0)),
            rank: row.get(4)?,
            alias_used: row.get(5)?,
            explanation: row.get(6)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(rankings)
}

/// Get provider performance comparison
pub fn get_provider_performance() -> Result<Vec<ProviderPerformance>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            r.provider_name,
            r.model_name,
            COUNT(DISTINCT m.id) as total_mentions,
            AVG(m.rank_position) as avg_rank,
            COUNT(DISTINCT r.id) as total_responses,
            COUNT(DISTINCT CASE WHEN r.error_message IS NULL THEN r.id END) as successful_responses
         FROM responses r
         LEFT JOIN mentions m ON r.id = m.response_id
         GROUP BY r.provider_name, r.model_name
         ORDER BY total_mentions DESC"
    )?;
    
    let performance = stmt.query_map([], |row| {
        let total_resp: i32 = row.get(4)?;
        let success_resp: i32 = row.get(5)?;
        let success_rate = if total_resp > 0 {
            (success_resp as f64 / total_resp as f64) * 100.0
        } else {
            0.0
        };
        
        Ok(ProviderPerformance {
            provider: row.get(0)?,
            model: row.get(1)?,
            total_mentions: row.get(2)?,
            avg_rank: row.get(3)?,
            total_responses: total_resp,
            successful_responses: success_resp,
            success_rate,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(performance)
}

/// Get competitor graph data
pub fn get_competitor_graph(min_strength: f64) -> Result<CompetitorGraph> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            brand_name_1,
            brand_name_2,
            co_mention_count,
            avg_rank_distance,
            strength_score
         FROM competitor_relationships
         WHERE strength_score >= ?
         ORDER BY strength_score DESC"
    )?;
    
    let mut nodes_set: HashMap<String, f64> = HashMap::new();
    let mut edges = Vec::new();
    
    let rows = stmt.query_map([min_strength], |row| {
        let brand1: String = row.get(0)?;
        let brand2: String = row.get(1)?;
        let co_mentions: i32 = row.get(2)?;
        let avg_distance: f64 = row.get(3)?;
        let weight: f64 = row.get(4)?;
        
        Ok((brand1, brand2, co_mentions, avg_distance, weight))
    })?;
    
    for row in rows.filter_map(|r| r.ok()) {
        let (brand1, brand2, co_mentions, avg_distance, weight) = row;
        
        // Track node sizes based on connection count
        *nodes_set.entry(brand1.clone()).or_insert(0.0) += 1.0;
        *nodes_set.entry(brand2.clone()).or_insert(0.0) += 1.0;
        
        edges.push(GraphEdge {
            source: brand1,
            target: brand2,
            weight,
            co_mentions,
            avg_distance,
        });
    }
    
    let nodes: Vec<GraphNode> = nodes_set
        .into_iter()
        .map(|(id, size)| GraphNode {
            label: id.clone(),
            id,
            size: Some(size + 10.0), // Base size + connections
        })
        .collect();
    
    let total_nodes = nodes.len();
    let total_edges = edges.len();
    
    Ok(CompetitorGraph {
        nodes,
        edges,
        total_nodes,
        total_edges,
    })
}

/// Get top competitors for a specific brand
pub fn get_brand_competitors(brand_name: &str, top_n: i32) -> Result<Vec<CompetitorRelationship>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            CASE 
                WHEN brand_name_1 = ? THEN brand_name_2
                ELSE brand_name_1
            END as competitor,
            brand_name_1,
            brand_name_2,
            co_mention_count,
            avg_rank_distance,
            strength_score,
            first_seen,
            last_seen
         FROM competitor_relationships
         WHERE brand_name_1 = ? OR brand_name_2 = ?
         ORDER BY strength_score DESC
         LIMIT ?"
    )?;
    
    let competitors = stmt.query_map(params![brand_name, brand_name, brand_name, top_n], |row| {
        Ok(CompetitorRelationship {
            brand_name_1: row.get(1)?,
            brand_name_2: row.get(2)?,
            co_mention_count: row.get(3)?,
            avg_rank_distance: row.get(4)?,
            strength_score: row.get(5)?,
            first_seen: row.get(6)?,
            last_seen: row.get(7)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(competitors)
}

/// Get hallucination scores
pub fn get_hallucination_scores() -> Result<Vec<HallucinationScore>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            hs.id,
            hs.mention_id,
            m.brand_name,
            hs.confidence_score,
            hs.reliability_score,
            hs.risk_level,
            hs.has_source,
            hs.source_accessible,
            hs.source_count
         FROM hallucination_scores hs
         JOIN mentions m ON hs.mention_id = m.id
         ORDER BY hs.reliability_score ASC"
    )?;
    
    let scores = stmt.query_map([], |row| {
        Ok(HallucinationScore {
            id: row.get(0)?,
            mention_id: row.get(1)?,
            brand_name: row.get(2)?,
            confidence_score: row.get(3)?,
            reliability_score: row.get(4)?,
            risk_level: row.get(5)?,
            has_source: row.get(6)?,
            source_accessible: row.get(7)?,
            source_count: row.get(8)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(scores)
}

/// Get response quality metrics
pub fn get_response_quality() -> Result<Vec<ResponseQuality>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            rq.response_id,
            r.provider_name,
            r.model_name,
            rq.avg_reliability,
            rq.high_risk_count,
            rq.medium_risk_count,
            rq.low_risk_count,
            rq.total_mentions,
            rq.overall_quality
         FROM response_quality rq
         JOIN responses r ON rq.response_id = r.id
         ORDER BY rq.avg_reliability DESC"
    )?;
    
    let quality = stmt.query_map([], |row| {
        Ok(ResponseQuality {
            response_id: row.get(0)?,
            provider_name: row.get(1)?,
            model_name: row.get(2)?,
            avg_reliability: row.get(3)?,
            high_risk_count: row.get(4)?,
            medium_risk_count: row.get(5)?,
            low_risk_count: row.get(6)?,
            total_mentions: row.get(7)?,
            overall_quality: row.get(8)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(quality)
}

/// Get sources for a specific mention
pub fn get_sources_for_mention(mention_id: i64) -> Result<Vec<Source>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            id, mention_id, url, title, description,
            is_valid, is_accessible, status_code, validation_error
         FROM sources
         WHERE mention_id = ?"
    )?;
    
    let sources = stmt.query_map([mention_id], |row| {
        Ok(Source {
            id: row.get(0)?,
            mention_id: row.get(1)?,
            url: row.get(2)?,
            title: row.get(3)?,
            description: row.get(4)?,
            is_valid: row.get(5)?,
            is_accessible: row.get(6)?,
            status_code: row.get(7)?,
            validation_error: row.get(8)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(sources)
}

/// Get all unique brand names
pub fn get_all_brands() -> Result<Vec<String>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT DISTINCT brand_name FROM mentions ORDER BY brand_name"
    )?;
    
    let brands = stmt.query_map([], |row| row.get(0))?
        .filter_map(|r| r.ok())
        .collect();
    
    Ok(brands)
}

/// Get recent mentions
pub fn get_recent_mentions(limit: i32) -> Result<Vec<BrandMention>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            m.id, m.brand_id, m.brand_name, m.alias_used,
            m.rank_position, m.explanation, m.response_id,
            m.match_method, m.match_confidence, m.match_reasoning
         FROM mentions m
         JOIN responses r ON m.response_id = r.id
         ORDER BY r.timestamp DESC
         LIMIT ?"
    )?;
    
    let mentions = stmt.query_map([limit], |row| {
        Ok(BrandMention {
            id: row.get(0)?,
            brand_id: row.get(1)?,
            brand_name: row.get(2)?,
            alias_used: row.get(3)?,
            rank_position: row.get(4)?,
            explanation: row.get(5)?,
            response_id: row.get(6)?,
            match_method: row.get(7)?,
            match_confidence: row.get(8)?,
            match_reasoning: row.get(9)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(mentions)
}

/// Get LLM evaluation statistics
pub fn get_evaluation_stats() -> Result<Vec<EvaluationStats>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            id, run_id, eval_method, total_evaluations,
            avg_confidence, high_confidence_count, low_confidence_count,
            fallback_count, timestamp
         FROM evaluation_stats
         ORDER BY timestamp DESC
         LIMIT 20"
    )?;
    
    let stats = stmt.query_map([], |row| {
        Ok(EvaluationStats {
            id: row.get(0)?,
            run_id: row.get(1)?,
            eval_method: row.get(2)?,
            total_evaluations: row.get(3)?,
            avg_confidence: row.get(4)?,
            high_confidence_count: row.get(5)?,
            low_confidence_count: row.get(6)?,
            fallback_count: row.get(7)?,
            timestamp: row.get(8)?,
        })
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(stats)
}

/// Get match confidence distribution
pub fn get_confidence_distribution() -> Result<Vec<(String, i32)>> {
    let conn = get_connection()?;
    
    let mut stmt = conn.prepare(
        "SELECT 
            CASE 
                WHEN match_confidence >= 0.9 THEN 'very_high'
                WHEN match_confidence >= 0.7 THEN 'high'
                WHEN match_confidence >= 0.5 THEN 'medium'
                WHEN match_confidence > 0 THEN 'low'
                ELSE 'none'
            END as confidence_level,
            COUNT(*) as count
         FROM mentions
         GROUP BY confidence_level
         ORDER BY 
            CASE confidence_level 
                WHEN 'very_high' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                WHEN 'low' THEN 4 
                ELSE 5 
            END"
    )?;
    
    let distribution = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, i32>(1)?))
    })?
    .filter_map(|r| r.ok())
    .collect();
    
    Ok(distribution)
}
