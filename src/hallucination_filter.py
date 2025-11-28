"""
Hallucination Filter - Verify LLM claims with sources and confidence scoring

This module provides tools to:
1. Extract and validate sources/URLs from LLM responses
2. Score confidence levels for each claim
3. Detect potential hallucinations based on source availability
4. Verify URL accessibility and relevance
"""

import re
import asyncio
import aiohttp
import sqlite3
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from collections import defaultdict


class SourceValidator:
    """Validates URLs and sources provided by LLMs"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.cache = {}  # Cache validation results
        
    async def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Validate if a URL is accessible and returns basic metadata
        
        Args:
            url: The URL to validate
            
        Returns:
            Dictionary with validation results
        """
        if url in self.cache:
            return self.cache[url]
            
        result = {
            "url": url,
            "is_valid": False,
            "is_accessible": False,
            "status_code": None,
            "content_type": None,
            "error": None
        }
        
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                result["error"] = "Invalid URL format"
                self.cache[url] = result
                return result
            result["is_valid"] = True
        except Exception as e:
            result["error"] = f"Parse error: {str(e)}"
            self.cache[url] = result
            return result
        
        # Check URL accessibility
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True
                ) as response:
                    result["is_accessible"] = response.status < 400
                    result["status_code"] = response.status
                    result["content_type"] = response.headers.get("Content-Type")
        except asyncio.TimeoutError:
            result["error"] = "Timeout"
        except aiohttp.ClientError as e:
            result["error"] = f"Client error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        self.cache[url] = result
        return result
    
    async def validate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate multiple sources concurrently
        
        Args:
            sources: List of source dictionaries with 'url' field
            
        Returns:
            List of validation results
        """
        tasks = []
        for source in sources:
            if "url" in source and source["url"]:
                tasks.append(self.validate_url(source["url"]))
        
        if not tasks:
            return []
            
        return await asyncio.gather(*tasks, return_exceptions=True)


class HallucinationScorer:
    """Scores potential hallucinations based on sources and confidence"""
    
    def __init__(self):
        self.weights = {
            "has_source": 0.3,
            "source_accessible": 0.3,
            "confidence_score": 0.4
        }
    
    def calculate_reliability_score(
        self, 
        has_source: bool,
        source_accessible: bool,
        confidence: float,
        source_count: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate reliability score for a claim
        
        Args:
            has_source: Whether source(s) are provided
            source_accessible: Whether source(s) are accessible
            confidence: LLM's self-reported confidence (0-1)
            source_count: Number of sources provided
            
        Returns:
            Dictionary with reliability metrics
        """
        # Base score calculation
        score = 0.0
        
        # Source availability bonus
        if has_source:
            score += self.weights["has_source"]
            # Extra credit for multiple sources
            if source_count > 1:
                score += min(0.1, 0.02 * (source_count - 1))
        
        # Source accessibility bonus
        if source_accessible:
            score += self.weights["source_accessible"]
        
        # Confidence score
        score += self.weights["confidence_score"] * confidence
        
        # Normalize to 0-1 range
        max_possible = sum(self.weights.values()) + 0.1  # Include max multi-source bonus
        normalized_score = min(1.0, score / max_possible)
        
        # Determine hallucination risk
        if normalized_score >= 0.7:
            risk_level = "low"
        elif normalized_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return {
            "reliability_score": normalized_score,
            "risk_level": risk_level,
            "has_source": has_source,
            "source_accessible": source_accessible,
            "confidence": confidence,
            "source_count": source_count
        }
    
    def analyze_response_quality(self, mentions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze overall quality of an LLM response based on all mentions
        
        Args:
            mentions: List of mention dictionaries with reliability scores
            
        Returns:
            Aggregate quality metrics
        """
        if not mentions:
            return {
                "avg_reliability": 0.0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "total_mentions": 0,
                "overall_quality": "poor"
            }
        
        total_score = sum(m.get("reliability_score", 0) for m in mentions)
        avg_score = total_score / len(mentions)
        
        risk_counts = defaultdict(int)
        for m in mentions:
            risk_counts[m.get("risk_level", "high")] += 1
        
        # Determine overall quality
        if avg_score >= 0.7 and risk_counts["high"] == 0:
            overall_quality = "excellent"
        elif avg_score >= 0.5 and risk_counts["high"] <= 1:
            overall_quality = "good"
        elif avg_score >= 0.3:
            overall_quality = "fair"
        else:
            overall_quality = "poor"
        
        return {
            "avg_reliability": avg_score,
            "high_risk_count": risk_counts["high"],
            "medium_risk_count": risk_counts["medium"],
            "low_risk_count": risk_counts["low"],
            "total_mentions": len(mentions),
            "overall_quality": overall_quality
        }


def create_hallucination_tables(conn):
    """Create database tables for hallucination tracking"""
    c = conn.cursor()
    
    # Table for sources
    c.execute('''CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mention_id INTEGER,
        url TEXT,
        title TEXT,
        description TEXT,
        is_valid BOOLEAN,
        is_accessible BOOLEAN,
        status_code INTEGER,
        content_type TEXT,
        validation_error TEXT,
        timestamp REAL,
        FOREIGN KEY (mention_id) REFERENCES mentions (id)
    )''')
    
    # Table for hallucination scores
    c.execute('''CREATE TABLE IF NOT EXISTS hallucination_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mention_id INTEGER,
        confidence_score REAL,
        reliability_score REAL,
        risk_level TEXT,
        has_source BOOLEAN,
        source_accessible BOOLEAN,
        source_count INTEGER,
        timestamp REAL,
        FOREIGN KEY (mention_id) REFERENCES mentions (id)
    )''')
    
    # Table for response quality metrics
    c.execute('''CREATE TABLE IF NOT EXISTS response_quality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        response_id INTEGER,
        avg_reliability REAL,
        high_risk_count INTEGER,
        medium_risk_count INTEGER,
        low_risk_count INTEGER,
        total_mentions INTEGER,
        overall_quality TEXT,
        timestamp REAL,
        FOREIGN KEY (response_id) REFERENCES responses (id)
    )''')
    
    conn.commit()


async def analyze_hallucinations(db_path: str = "llmseo.db", verify_urls: bool = True):
    """
    Analyze existing responses for potential hallucinations
    
    Args:
        db_path: Path to SQLite database
        verify_urls: Whether to verify URL accessibility (can be slow)
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    create_hallucination_tables(conn)
    
    print("Analyzing responses for hallucination risks...\n")
    
    # Get all responses with their mentions and sources
    c.execute('''
        SELECT 
            r.id as response_id,
            m.id as mention_id,
            m.brand_name,
            r.provider_name,
            r.model_name,
            r.query_id
        FROM responses r
        LEFT JOIN mentions m ON r.id = m.response_id
        WHERE r.error_message IS NULL
        ORDER BY r.id, m.rank_position
    ''')
    
    responses = c.fetchall()
    
    if not responses:
        print("No responses found to analyze")
        conn.close()
        return
    
    # Group by response_id
    response_groups = defaultdict(list)
    for row in responses:
        response_id = row[0]
        response_groups[response_id].append({
            "mention_id": row[1],
            "brand_name": row[2],
            "provider": row[3],
            "model": row[4],
            "query_id": row[5]
        })
    
    validator = SourceValidator() if verify_urls else None
    scorer = HallucinationScorer()
    
    total_analyzed = 0
    
    for response_id, mentions in response_groups.items():
        print(f"Analyzing Response #{response_id}")
        
        mention_scores = []
        
        for mention in mentions:
            if mention["mention_id"] is None:
                continue
                
            mention_id = mention["mention_id"]
            
            # Check if sources exist for this mention
            c.execute('SELECT url FROM sources WHERE mention_id = ?', (mention_id,))
            sources = c.fetchall()
            
            has_source = len(sources) > 0
            source_accessible = False
            
            # Validate sources if requested
            if verify_urls and sources and validator:
                validation_results = await validator.validate_sources(
                    [{"url": s[0]} for s in sources]
                )
                source_accessible = any(
                    r.get("is_accessible", False) for r in validation_results
                    if isinstance(r, dict)
                )
            
            # For now, use a default confidence if not stored
            # In production, this would come from the LLM response
            confidence = 0.7 if has_source else 0.5
            
            # Calculate reliability score
            score_result = scorer.calculate_reliability_score(
                has_source=has_source,
                source_accessible=source_accessible,
                confidence=confidence,
                source_count=len(sources)
            )
            
            # Store hallucination score
            c.execute('''INSERT INTO hallucination_scores 
                        (mention_id, confidence_score, reliability_score, risk_level,
                         has_source, source_accessible, source_count, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (mention_id, confidence, score_result["reliability_score"],
                      score_result["risk_level"], has_source, source_accessible,
                      len(sources), time.time()))
            
            mention_scores.append(score_result)
            
            print(f"  - {mention['brand_name']}: "
                  f"Reliability={score_result['reliability_score']:.2f}, "
                  f"Risk={score_result['risk_level']}")
            
            total_analyzed += 1
        
        # Calculate overall response quality
        quality = scorer.analyze_response_quality(mention_scores)
        
        c.execute('''INSERT INTO response_quality
                    (response_id, avg_reliability, high_risk_count, medium_risk_count,
                     low_risk_count, total_mentions, overall_quality, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (response_id, quality["avg_reliability"], quality["high_risk_count"],
                  quality["medium_risk_count"], quality["low_risk_count"],
                  quality["total_mentions"], quality["overall_quality"], time.time()))
        
        print(f"  Overall Quality: {quality['overall_quality']} "
              f"(Avg Reliability: {quality['avg_reliability']:.2f})\n")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Analyzed {total_analyzed} mentions across {len(response_groups)} responses")


def print_hallucination_report(db_path: str = "llmseo.db"):
    """Print a comprehensive hallucination analysis report"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("\n" + "="*70)
    print("HALLUCINATION RISK REPORT")
    print("="*70 + "\n")
    
    # Overall statistics
    c.execute('''
        SELECT 
            COUNT(*) as total,
            AVG(reliability_score) as avg_reliability,
            SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high_risk,
            SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) as medium_risk,
            SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) as low_risk,
            SUM(CASE WHEN has_source = 1 THEN 1 ELSE 0 END) as with_sources,
            SUM(CASE WHEN source_accessible = 1 THEN 1 ELSE 0 END) as accessible_sources
        FROM hallucination_scores
    ''')
    
    stats = c.fetchone()
    
    if stats[0] == 0:
        print("No hallucination scores found. Run analysis first.")
        conn.close()
        return
    
    total, avg_rel, high, medium, low, with_sources, accessible = stats
    
    print("OVERALL STATISTICS")
    print("-" * 70)
    print(f"Total Mentions Analyzed: {total}")
    print(f"Average Reliability Score: {avg_rel:.2f}")
    print(f"\nRisk Distribution:")
    print(f"  🔴 High Risk: {high} ({high/total*100:.1f}%)")
    print(f"  🟡 Medium Risk: {medium} ({medium/total*100:.1f}%)")
    print(f"  🟢 Low Risk: {low} ({low/total*100:.1f}%)")
    print(f"\nSource Coverage:")
    print(f"  With Sources: {with_sources} ({with_sources/total*100:.1f}%)")
    print(f"  Accessible Sources: {accessible} ({accessible/total*100:.1f}%)")
    
    # Provider comparison
    print("\n" + "="*70)
    print("PROVIDER COMPARISON")
    print("="*70)
    
    c.execute('''
        SELECT 
            r.provider_name,
            r.model_name,
            AVG(hs.reliability_score) as avg_reliability,
            SUM(CASE WHEN hs.risk_level = 'high' THEN 1 ELSE 0 END) as high_risk,
            SUM(CASE WHEN hs.has_source = 1 THEN 1 ELSE 0 END) as with_sources,
            COUNT(*) as total_mentions
        FROM hallucination_scores hs
        JOIN mentions m ON hs.mention_id = m.id
        JOIN responses r ON m.response_id = r.id
        GROUP BY r.provider_name, r.model_name
        ORDER BY avg_reliability DESC
    ''')
    
    providers = c.fetchall()
    
    print(f"\n{'Provider':<15} {'Model':<15} {'Avg Reliability':<18} {'High Risk':<12} {'With Sources'}")
    print("-" * 70)
    
    for row in providers:
        provider, model, avg_rel, high_risk, with_src, total = row
        print(f"{provider:<15} {model:<15} {avg_rel:<18.2f} {high_risk:<12} {with_src}/{total}")
    
    # High risk mentions
    print("\n" + "="*70)
    print("HIGH RISK MENTIONS (Potential Hallucinations)")
    print("="*70 + "\n")
    
    c.execute('''
        SELECT 
            m.brand_name,
            m.alias_used,
            m.rank_position,
            r.provider_name,
            r.model_name,
            hs.reliability_score,
            hs.has_source,
            hs.source_accessible
        FROM hallucination_scores hs
        JOIN mentions m ON hs.mention_id = m.id
        JOIN responses r ON m.response_id = r.id
        WHERE hs.risk_level = 'high'
        ORDER BY hs.reliability_score ASC
        LIMIT 10
    ''')
    
    high_risk_mentions = c.fetchall()
    
    if high_risk_mentions:
        for row in high_risk_mentions:
            brand, alias, rank, provider, model, reliability, has_src, src_acc = row
            print(f"🔴 {brand} (as '{alias}') - Rank #{rank}")
            print(f"   Provider: {provider}/{model}")
            print(f"   Reliability: {reliability:.2f}")
            print(f"   Sources: {'Yes' if has_src else 'No'} | "
                  f"Accessible: {'Yes' if src_acc else 'No'}")
            print()
    else:
        print("No high-risk mentions found!")
    
    conn.close()


async def main():
    """Main function for hallucination analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hallucination Filter Analysis')
    parser.add_argument('--db', default='llmseo.db', help='Database file path')
    parser.add_argument('--analyze', action='store_true', help='Run hallucination analysis')
    parser.add_argument('--report', action='store_true', help='Show hallucination report')
    parser.add_argument('--verify-urls', action='store_true', 
                       help='Verify URL accessibility (slower)')
    
    args = parser.parse_args()
    
    if args.analyze:
        await analyze_hallucinations(args.db, verify_urls=args.verify_urls)
    
    if args.report or (not args.analyze):
        print_hallucination_report(args.db)


if __name__ == "__main__":
    asyncio.run(main())
