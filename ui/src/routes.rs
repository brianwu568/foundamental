use rocket::serde::json::Json;
use rocket::{Route, routes, get};
use rocket_dyn_templates::{Template, context};
use crate::db;
use crate::models::*;

// =====================
// HTML Page Routes
// =====================

#[get("/")]
pub fn index() -> Template {
    let stats = db::get_dashboard_stats().unwrap_or_else(|_| DashboardStats {
        total_brands: 0,
        total_responses: 0,
        total_mentions: 0,
        total_co_mentions: 0,
        avg_reliability: 0.0,
        high_risk_count: 0,
        medium_risk_count: 0,
        low_risk_count: 0,
        llm_match_count: 0,
        regex_match_count: 0,
        avg_match_confidence: 0.0,
    });
    
    let recent_mentions = db::get_recent_mentions(10).unwrap_or_default();
    let providers = db::get_provider_performance().unwrap_or_default();
    
    Template::render("index", context! {
        title: "Dashboard",
        stats: stats,
        recent_mentions: recent_mentions,
        providers: providers,
    })
}

#[get("/brands")]
pub fn brands_page() -> Template {
    let rankings = db::get_brand_rankings().unwrap_or_default();
    let brands = db::get_all_brands().unwrap_or_default();
    
    Template::render("brands", context! {
        title: "Brand Rankings",
        rankings: rankings,
        brands: brands,
    })
}

#[get("/competitors")]
pub fn competitors_page() -> Template {
    let graph = db::get_competitor_graph(0.0).unwrap_or_else(|_| CompetitorGraph {
        nodes: vec![],
        edges: vec![],
        total_nodes: 0,
        total_edges: 0,
    });
    
    let brands = db::get_all_brands().unwrap_or_default();
    
    Template::render("competitors", context! {
        title: "Competitor Graph",
        graph: graph,
        brands: brands,
    })
}

#[get("/hallucinations")]
pub fn hallucinations_page() -> Template {
    let scores = db::get_hallucination_scores().unwrap_or_default();
    let quality = db::get_response_quality().unwrap_or_default();
    
    Template::render("hallucinations", context! {
        title: "Hallucination Filter",
        scores: scores,
        quality: quality,
    })
}

#[get("/providers")]
pub fn providers_page() -> Template {
    let providers = db::get_provider_performance().unwrap_or_default();
    
    Template::render("providers", context! {
        title: "Provider Performance",
        providers: providers,
    })
}

// =====================
// JSON API Routes
// =====================

#[get("/stats")]
pub fn api_stats() -> Json<DashboardStats> {
    let stats = db::get_dashboard_stats().unwrap_or_else(|_| DashboardStats {
        total_brands: 0,
        total_responses: 0,
        total_mentions: 0,
        total_co_mentions: 0,
        avg_reliability: 0.0,
        high_risk_count: 0,
        medium_risk_count: 0,
        low_risk_count: 0,
        llm_match_count: 0,
        regex_match_count: 0,
        avg_match_confidence: 0.0,
    });
    
    Json(stats)
}

#[get("/brands")]
pub fn api_brands() -> Json<Vec<String>> {
    let brands = db::get_all_brands().unwrap_or_default();
    Json(brands)
}

#[get("/rankings")]
pub fn api_rankings() -> Json<Vec<BrandRanking>> {
    let rankings = db::get_brand_rankings().unwrap_or_default();
    Json(rankings)
}

#[get("/providers")]
pub fn api_providers() -> Json<Vec<ProviderPerformance>> {
    let providers = db::get_provider_performance().unwrap_or_default();
    Json(providers)
}

#[get("/graph?<min_strength>")]
pub fn api_graph(min_strength: Option<f64>) -> Json<CompetitorGraph> {
    let strength = min_strength.unwrap_or(0.0);
    let graph = db::get_competitor_graph(strength).unwrap_or_else(|_| CompetitorGraph {
        nodes: vec![],
        edges: vec![],
        total_nodes: 0,
        total_edges: 0,
    });
    
    Json(graph)
}

#[get("/competitors/<brand>?<top_n>")]
pub fn api_brand_competitors(brand: &str, top_n: Option<i32>) -> Json<Vec<CompetitorRelationship>> {
    let n = top_n.unwrap_or(5);
    let competitors = db::get_brand_competitors(brand, n).unwrap_or_default();
    Json(competitors)
}

#[get("/hallucinations")]
pub fn api_hallucinations() -> Json<Vec<HallucinationScore>> {
    let scores = db::get_hallucination_scores().unwrap_or_default();
    Json(scores)
}

#[get("/quality")]
pub fn api_quality() -> Json<Vec<ResponseQuality>> {
    let quality = db::get_response_quality().unwrap_or_default();
    Json(quality)
}

#[get("/sources/<mention_id>")]
pub fn api_sources(mention_id: i64) -> Json<Vec<Source>> {
    let sources = db::get_sources_for_mention(mention_id).unwrap_or_default();
    Json(sources)
}

#[get("/mentions?<limit>")]
pub fn api_mentions(limit: Option<i32>) -> Json<Vec<BrandMention>> {
    let l = limit.unwrap_or(50);
    let mentions = db::get_recent_mentions(l).unwrap_or_default();
    Json(mentions)
}

#[get("/evaluation-stats")]
pub fn api_evaluation_stats() -> Json<Vec<EvaluationStats>> {
    let stats = db::get_evaluation_stats().unwrap_or_default();
    Json(stats)
}

#[get("/confidence-distribution")]
pub fn api_confidence_distribution() -> Json<Vec<(String, i32)>> {
    let distribution = db::get_confidence_distribution().unwrap_or_default();
    Json(distribution)
}

// =====================
// Route Collections
// =====================

pub fn index_routes() -> Vec<Route> {
    routes![
        index,
        brands_page,
        competitors_page,
        hallucinations_page,
        providers_page,
    ]
}

pub fn api_routes() -> Vec<Route> {
    routes![
        api_stats,
        api_brands,
        api_rankings,
        api_providers,
        api_graph,
        api_brand_competitors,
        api_hallucinations,
        api_quality,
        api_sources,
        api_mentions,
        api_evaluation_stats,
        api_confidence_distribution,
    ]
}
