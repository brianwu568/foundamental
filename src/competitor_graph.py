"""
Competitor Graph Analysis - Co-mention network tracking over time

This module analyzes how brands are mentioned together in LLM responses,
building a temporal graph of competitive relationships.
"""

import sqlite3
import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import argparse


class CompetitorGraphAnalyzer:
    """Analyzes co-mention patterns to build competitor graphs"""
    
    def __init__(self, db_path: str = "llmseo.db"):
        self.db_path = db_path
        self.conn = None
    
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_tables()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
    
    def _ensure_tables(self):
        """Create co-mention tracking tables if they don't exist"""
        c = self.conn.cursor()
        
        # Table for co-mention relationships
        c.execute('''CREATE TABLE IF NOT EXISTS co_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id INTEGER,
            brand_id_1 INTEGER,
            brand_id_2 INTEGER,
            brand_name_1 TEXT,
            brand_name_2 TEXT,
            rank_1 INTEGER,
            rank_2 INTEGER,
            rank_distance INTEGER,
            query_id INTEGER,
            provider_name TEXT,
            model_name TEXT,
            timestamp REAL,
            FOREIGN KEY (response_id) REFERENCES responses (id)
        )''')
        
        # Table for aggregated competitor relationships over time
        c.execute('''CREATE TABLE IF NOT EXISTS competitor_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id_1 INTEGER,
            brand_id_2 INTEGER,
            brand_name_1 TEXT,
            brand_name_2 TEXT,
            co_mention_count INTEGER,
            avg_rank_distance REAL,
            first_seen REAL,
            last_seen REAL,
            strength_score REAL,
            PRIMARY KEY (brand_id_1, brand_id_2)
        ) WITHOUT ROWID''')
        
        # Index for efficient querying
        c.execute('''CREATE INDEX IF NOT EXISTS idx_co_mentions_brands 
                    ON co_mentions(brand_id_1, brand_id_2)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_co_mentions_timestamp 
                    ON co_mentions(timestamp)''')
        
        self.conn.commit()
    
    def extract_co_mentions(self) -> int:
        """
        Extract co-mention relationships from existing mentions table
        Returns the number of new co-mentions found
        """
        c = self.conn.cursor()
        
        # Find all responses with multiple brand mentions
        c.execute('''
            SELECT 
                m1.response_id,
                m1.brand_id,
                m1.brand_name,
                m1.rank_position,
                m2.brand_id,
                m2.brand_name,
                m2.rank_position,
                r.query_id,
                r.provider_name,
                r.model_name,
                r.timestamp
            FROM mentions m1
            JOIN mentions m2 ON m1.response_id = m2.response_id 
                AND m1.brand_id < m2.brand_id
            JOIN responses r ON m1.response_id = r.id
            WHERE r.error_message IS NULL
            ORDER BY r.timestamp DESC
        ''')
        
        co_mentions = c.fetchall()
        
        if not co_mentions:
            return 0
        
        # Check which ones are already recorded
        c.execute('SELECT MAX(id) FROM co_mentions')
        last_id = c.fetchone()[0] or 0
        
        new_count = 0
        
        for row in co_mentions:
            (response_id, brand_id_1, brand_name_1, rank_1,
             brand_id_2, brand_name_2, rank_2,
             query_id, provider, model, timestamp) = row
            
            rank_distance = abs(rank_1 - rank_2)
            
            # Check if this co-mention already exists
            c.execute('''
                SELECT id FROM co_mentions 
                WHERE response_id = ? 
                AND brand_id_1 = ? 
                AND brand_id_2 = ?
            ''', (response_id, brand_id_1, brand_id_2))
            
            if not c.fetchone():
                c.execute('''
                    INSERT INTO co_mentions 
                    (response_id, brand_id_1, brand_id_2, 
                     brand_name_1, brand_name_2, rank_1, rank_2, 
                     rank_distance, query_id, provider_name, 
                     model_name, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (response_id, brand_id_1, brand_id_2,
                      brand_name_1, brand_name_2, rank_1, rank_2,
                      rank_distance, query_id, provider, model, timestamp))
                new_count += 1
        
        self.conn.commit()
        return new_count
    
    def update_competitor_relationships(self):
        """
        Update aggregated competitor relationships based on co-mentions
        Calculates strength scores based on frequency and rank proximity
        """
        c = self.conn.cursor()
        
        # Clear existing relationships
        c.execute('DELETE FROM competitor_relationships')
        
        # Aggregate co-mention data
        c.execute('''
            SELECT 
                brand_id_1,
                brand_id_2,
                brand_name_1,
                brand_name_2,
                COUNT(*) as co_mention_count,
                AVG(rank_distance) as avg_rank_distance,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM co_mentions
            GROUP BY brand_id_1, brand_id_2
        ''')
        
        relationships = c.fetchall()
        
        for row in relationships:
            (brand_id_1, brand_id_2, brand_name_1, brand_name_2,
             co_mention_count, avg_rank_distance, first_seen, last_seen) = row
            
            # Calculate strength score
            # Higher frequency = stronger relationship
            # Lower rank distance = stronger relationship
            # Normalize: frequency (0-1) * proximity_factor (0-1)
            max_distance = 10  # Assume max distance is 10
            proximity_factor = 1 - min(avg_rank_distance, max_distance) / max_distance
            
            # Simple strength calculation - can be enhanced
            strength_score = (min(co_mention_count / 10, 1.0) * 0.6 + 
                            proximity_factor * 0.4)
            
            c.execute('''
                INSERT INTO competitor_relationships
                (brand_id_1, brand_id_2, brand_name_1, brand_name_2,
                 co_mention_count, avg_rank_distance, first_seen, 
                 last_seen, strength_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (brand_id_1, brand_id_2, brand_name_1, brand_name_2,
                  co_mention_count, avg_rank_distance, first_seen,
                  last_seen, strength_score))
        
        self.conn.commit()
        return len(relationships)
    
    def get_competitor_graph(self, brand_id: Optional[int] = None, 
                            min_strength: float = 0.0) -> Dict[str, Any]:
        """
        Get competitor graph data
        
        Args:
            brand_id: Filter by specific brand (None = all brands)
            min_strength: Minimum strength score to include
            
        Returns:
            Dictionary with nodes and edges for graph visualization
        """
        c = self.conn.cursor()
        
        # Build query based on filters
        where_clauses = ['strength_score >= ?']
        params = [min_strength]
        
        if brand_id is not None:
            where_clauses.append('(brand_id_1 = ? OR brand_id_2 = ?)')
            params.extend([brand_id, brand_id])
        
        where_sql = ' AND '.join(where_clauses)
        
        c.execute(f'''
            SELECT 
                brand_name_1,
                brand_name_2,
                co_mention_count,
                avg_rank_distance,
                strength_score,
                first_seen,
                last_seen
            FROM competitor_relationships
            WHERE {where_sql}
            ORDER BY strength_score DESC
        ''', params)
        
        edges = c.fetchall()
        
        # Build nodes set
        nodes = set()
        edge_list = []
        
        for row in edges:
            (brand1, brand2, count, avg_dist, strength, 
             first_seen, last_seen) = row
            
            nodes.add(brand1)
            nodes.add(brand2)
            
            edge_list.append({
                "source": brand1,
                "target": brand2,
                "weight": strength,
                "co_mentions": count,
                "avg_distance": round(avg_dist, 2),
                "first_seen": datetime.fromtimestamp(first_seen).isoformat(),
                "last_seen": datetime.fromtimestamp(last_seen).isoformat()
            })
        
        return {
            "nodes": [{"id": node, "label": node} for node in sorted(nodes)],
            "edges": edge_list,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edge_list),
                "min_strength_filter": min_strength
            }
        }
    
    def get_temporal_evolution(self, days: int = 30, 
                               window_days: int = 7) -> List[Dict[str, Any]]:
        """
        Get temporal evolution of competitor relationships
        
        Args:
            days: Number of days to look back
            window_days: Rolling window size in days
            
        Returns:
            List of time-windowed graph snapshots
        """
        c = self.conn.cursor()
        
        # Get timestamp range
        now = datetime.now().timestamp()
        start_time = (datetime.now() - timedelta(days=days)).timestamp()
        
        snapshots = []
        current_time = start_time
        window_seconds = window_days * 86400
        
        while current_time < now:
            window_start = current_time
            window_end = current_time + window_seconds
            
            c.execute('''
                SELECT 
                    brand_name_1,
                    brand_name_2,
                    COUNT(*) as count,
                    AVG(rank_distance) as avg_distance
                FROM co_mentions
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY brand_id_1, brand_id_2
            ''', (window_start, window_end))
            
            results = c.fetchall()
            
            if results:
                edges = []
                for brand1, brand2, count, avg_dist in results:
                    edges.append({
                        "source": brand1,
                        "target": brand2,
                        "count": count,
                        "avg_distance": round(avg_dist, 2)
                    })
                
                snapshots.append({
                    "window_start": datetime.fromtimestamp(window_start).isoformat(),
                    "window_end": datetime.fromtimestamp(window_end).isoformat(),
                    "edges": edges,
                    "edge_count": len(edges)
                })
            
            current_time += window_seconds
        
        return snapshots
    
    def get_brand_competitors(self, brand_name: str, 
                             top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get top competitors for a specific brand
        
        Args:
            brand_name: Name of the brand to analyze
            top_n: Number of top competitors to return
            
        Returns:
            List of competitor dictionaries sorted by strength
        """
        c = self.conn.cursor()
        
        c.execute('''
            SELECT 
                CASE 
                    WHEN brand_name_1 = ? THEN brand_name_2
                    ELSE brand_name_1
                END as competitor,
                co_mention_count,
                avg_rank_distance,
                strength_score,
                first_seen,
                last_seen
            FROM competitor_relationships
            WHERE brand_name_1 = ? OR brand_name_2 = ?
            ORDER BY strength_score DESC
            LIMIT ?
        ''', (brand_name, brand_name, brand_name, top_n))
        
        results = c.fetchall()
        
        competitors = []
        for row in results:
            competitor, count, avg_dist, strength, first, last = row
            competitors.append({
                "name": competitor,
                "co_mentions": count,
                "avg_rank_distance": round(avg_dist, 2),
                "strength": round(strength, 3),
                "relationship_age_days": round((last - first) / 86400, 1),
                "last_seen": datetime.fromtimestamp(last).isoformat()
            })
        
        return competitors


def print_competitor_graph_report(db_path: str = "llmseo.db", 
                                 brand_name: Optional[str] = None):
    """Print a comprehensive competitor graph report"""
    
    with CompetitorGraphAnalyzer(db_path) as analyzer:
        print("\n" + "="*70)
        print("COMPETITOR GRAPH ANALYSIS")
        print("="*70 + "\n")
        
        # Extract and update data
        print("Analyzing co-mention patterns...")
        new_co_mentions = analyzer.extract_co_mentions()
        print(f"✓ Found {new_co_mentions} new co-mentions")
        
        relationships_count = analyzer.update_competitor_relationships()
        print(f"✓ Updated {relationships_count} competitor relationships\n")
        
        if relationships_count == 0:
            print("No competitor relationships found.")
            print("Brands need to be mentioned together in responses to build the graph.")
            return
        
        # Overall network statistics
        graph = analyzer.get_competitor_graph(min_strength=0.0)
        print(f"NETWORK STATISTICS")
        print("-" * 70)
        print(f"Total Brands: {graph['metadata']['total_nodes']}")
        print(f"Total Relationships: {graph['metadata']['total_edges']}")
        
        # Top relationships
        print(f"\nSTRONGEST COMPETITOR RELATIONSHIPS")
        print("-" * 70)
        top_edges = sorted(graph['edges'], key=lambda x: x['weight'], reverse=True)[:10]
        
        for i, edge in enumerate(top_edges, 1):
            print(f"{i}. {edge['source']} ↔ {edge['target']}")
            print(f"   Strength: {edge['weight']:.3f} | "
                  f"Co-mentions: {edge['co_mentions']} | "
                  f"Avg Rank Distance: {edge['avg_distance']}")
        
        # Brand-specific analysis
        if brand_name:
            print(f"\n{brand_name.upper()} - COMPETITOR ANALYSIS")
            print("-" * 70)
            competitors = analyzer.get_brand_competitors(brand_name, top_n=10)
            
            if competitors:
                for i, comp in enumerate(competitors, 1):
                    print(f"{i}. {comp['name']}")
                    print(f"   Strength: {comp['strength']} | "
                          f"Co-mentions: {comp['co_mentions']} | "
                          f"Avg Distance: {comp['avg_rank_distance']} ranks")
                    print(f"   Relationship Age: {comp['relationship_age_days']} days | "
                          f"Last Seen: {comp['last_seen']}")
            else:
                print(f"No competitors found for {brand_name}")
        
        # Temporal evolution
        print(f"\nTEMPORAL EVOLUTION (Last 30 Days)")
        print("-" * 70)
        evolution = analyzer.get_temporal_evolution(days=30, window_days=7)
        
        if evolution:
            for snapshot in evolution:
                print(f"\n{snapshot['window_start'][:10]} to {snapshot['window_end'][:10]}")
                print(f"  Active Relationships: {snapshot['edge_count']}")
                if snapshot['edge_count'] > 0:
                    top_3 = sorted(snapshot['edges'], 
                                  key=lambda x: x['count'], 
                                  reverse=True)[:3]
                    for edge in top_3:
                        print(f"    • {edge['source']} ↔ {edge['target']} "
                              f"({edge['count']} mentions)")
        else:
            print("Not enough historical data for temporal analysis")


def export_competitor_graph(db_path: str = "llmseo.db", 
                           output_file: str = "competitor_graph.json",
                           min_strength: float = 0.0):
    """Export competitor graph to JSON for external visualization"""
    
    with CompetitorGraphAnalyzer(db_path) as analyzer:
        # Extract latest data
        analyzer.extract_co_mentions()
        analyzer.update_competitor_relationships()
        
        # Get graph data
        graph = analyzer.get_competitor_graph(min_strength=min_strength)
        evolution = analyzer.get_temporal_evolution(days=90, window_days=7)
        
        export_data = {
            "graph": graph,
            "temporal_evolution": evolution,
            "generated_at": datetime.now().isoformat(),
            "min_strength_threshold": min_strength
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✓ Competitor graph exported to {output_file}")
        print(f"  Nodes: {graph['metadata']['total_nodes']}")
        print(f"  Edges: {graph['metadata']['total_edges']}")
        print(f"  Time Windows: {len(evolution)}")


def main():
    """Main CLI for competitor graph analysis"""
    parser = argparse.ArgumentParser(
        description='Competitor Graph Analysis - Track co-mention networks over time')
    parser.add_argument('--db', default='llmseo.db', help='Database file path')
    parser.add_argument('--report', action='store_true', 
                       help='Show competitor graph report')
    parser.add_argument('--brand', type=str, 
                       help='Focus analysis on specific brand')
    parser.add_argument('--export', type=str, 
                       help='Export graph to JSON file')
    parser.add_argument('--min-strength', type=float, default=0.0,
                       help='Minimum relationship strength (0.0-1.0)')
    
    args = parser.parse_args()
    
    if args.export:
        export_competitor_graph(args.db, args.export, args.min_strength)
    elif args.report or args.brand:
        print_competitor_graph_report(args.db, args.brand)
    else:
        # Default: show report
        print_competitor_graph_report(args.db)


if __name__ == "__main__":
    main()
