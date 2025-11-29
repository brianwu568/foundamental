"""
Competitor Graph Demo

Demonstrates the competitor graph feature with example usage patterns.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from competitor_graph import CompetitorGraphAnalyzer, print_competitor_graph_report


def example_1_basic_analysis():
    """Example 1: Basic competitor graph analysis"""
    print("="*70)
    print("EXAMPLE 1: Basic Competitor Graph Analysis")
    print("="*70 + "\n")
    
    with CompetitorGraphAnalyzer("llmseo.db") as analyzer:
        # Extract co-mentions from existing data
        print("Extracting co-mention relationships...")
        new_co_mentions = analyzer.extract_co_mentions()
        print(f"✓ Found {new_co_mentions} new co-mentions\n")
        
        # Update aggregated relationships
        print("Updating competitor relationships...")
        relationships = analyzer.update_competitor_relationships()
        print(f"✓ Updated {relationships} relationships\n")
        
        # Get the graph
        graph = analyzer.get_competitor_graph()
        
        print(f"Network Overview:")
        print(f"  Brands: {graph['metadata']['total_nodes']}")
        print(f"  Relationships: {graph['metadata']['total_edges']}\n")
        
        print("Top 5 Strongest Relationships:")
        for i, edge in enumerate(sorted(graph['edges'], 
                                       key=lambda x: x['weight'], 
                                       reverse=True)[:5], 1):
            print(f"  {i}. {edge['source']} ↔ {edge['target']}")
            print(f"     Strength: {edge['weight']:.3f}, "
                  f"Co-mentions: {edge['co_mentions']}")


def example_2_brand_specific():
    """Example 2: Analyze competitors for a specific brand"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Brand-Specific Competitor Analysis")
    print("="*70 + "\n")
    
    brand_name = "YourBrand"  # Change to a brand from your config
    
    with CompetitorGraphAnalyzer("llmseo.db") as analyzer:
        analyzer.extract_co_mentions()
        analyzer.update_competitor_relationships()
        
        competitors = analyzer.get_brand_competitors(brand_name, top_n=5)
        
        if competitors:
            print(f"Top 5 Competitors for {brand_name}:\n")
            for i, comp in enumerate(competitors, 1):
                print(f"{i}. {comp['name']}")
                print(f"   Strength Score: {comp['strength']}")
                print(f"   Co-mentions: {comp['co_mentions']}")
                print(f"   Avg Rank Distance: {comp['avg_rank_distance']}")
                print(f"   Relationship Age: {comp['relationship_age_days']} days")
                print(f"   Last Seen: {comp['last_seen']}\n")
        else:
            print(f"No competitors found for {brand_name}")
            print("Try running: python foundamental.py run")


def example_3_temporal_evolution():
    """Example 3: Track how relationships evolve over time"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Temporal Evolution Analysis")
    print("="*70 + "\n")
    
    with CompetitorGraphAnalyzer("llmseo.db") as analyzer:
        analyzer.extract_co_mentions()
        
        # Get 30-day evolution with weekly windows
        evolution = analyzer.get_temporal_evolution(days=30, window_days=7)
        
        if evolution:
            print(f"Analyzing {len(evolution)} time windows...\n")
            
            for snapshot in evolution:
                print(f"Week: {snapshot['window_start'][:10]} to "
                      f"{snapshot['window_end'][:10]}")
                print(f"  Active Relationships: {snapshot['edge_count']}")
                
                if snapshot['edges']:
                    top = sorted(snapshot['edges'], 
                               key=lambda x: x['count'], 
                               reverse=True)[:3]
                    for edge in top:
                        print(f"    • {edge['source']} ↔ {edge['target']} "
                              f"({edge['count']} mentions)")
                print()
        else:
            print("Not enough historical data for temporal analysis")
            print("Run analyses over multiple days to see trends")


def example_4_export_for_visualization():
    """Example 4: Export graph data for visualization"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Export Graph for Visualization")
    print("="*70 + "\n")
    
    from competitor_graph import export_competitor_graph
    
    output_file = "competitor_graph_demo.json"
    
    print("Exporting competitor graph to JSON...\n")
    export_competitor_graph(
        db_path="llmseo.db",
        output_file=output_file,
        min_strength=0.3  # Only include moderate-to-strong relationships
    )
    
    print(f"\n✓ Graph exported to {output_file}")
    print("\nYou can now use this JSON file with:")
    print("  • D3.js force-directed graph")
    print("  • Gephi for network analysis")
    print("  • Custom visualization tools")
    print("  • NetworkX in Python")


def example_5_custom_queries():
    """Example 5: Custom SQL queries for advanced insights"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Custom SQL Queries")
    print("="*70 + "\n")
    
    import sqlite3
    
    conn = sqlite3.connect("llmseo.db")
    c = conn.cursor()
    
    # Query 1: Co-mentions by provider
    print("Co-mentions grouped by provider:\n")
    c.execute('''
        SELECT 
            provider_name,
            COUNT(*) as total_co_mentions,
            COUNT(DISTINCT brand_id_1) as unique_brands_1,
            COUNT(DISTINCT brand_id_2) as unique_brands_2
        FROM co_mentions
        GROUP BY provider_name
        ORDER BY total_co_mentions DESC
    ''')
    
    results = c.fetchall()
    for provider, total, brands1, brands2 in results:
        print(f"  {provider}: {total} co-mentions "
              f"({max(brands1, brands2)} unique brands)")
    
    # Query 2: Average rank distance by brand
    print("\n\nAverage rank distance when brands co-occur:\n")
    c.execute('''
        SELECT 
            brand_name_1,
            AVG(rank_distance) as avg_distance,
            COUNT(*) as occurrences
        FROM co_mentions
        GROUP BY brand_name_1
        HAVING occurrences >= 3
        ORDER BY avg_distance ASC
    ''')
    
    results = c.fetchall()
    for brand, avg_dist, count in results[:5]:
        print(f"  {brand}: {avg_dist:.2f} average ranks apart "
              f"({count} co-mentions)")
    
    conn.close()


def main():
    """Run all examples"""
    print("\n🔍 Competitor Graph Feature Demo\n")
    
    import sqlite3
    
    # Check if database exists and has data
    try:
        conn = sqlite3.connect("llmseo.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM mentions")
        mention_count = c.fetchone()[0]
        conn.close()
        
        if mention_count == 0:
            print("⚠️  No data found in database!")
            print("\nPlease run an analysis first:")
            print("  python foundamental.py run\n")
            return
        
        print(f"✓ Found {mention_count} brand mentions in database\n")
        
    except Exception as e:
        print(f"⚠️  Could not access database: {e}")
        print("\nPlease run an analysis first:")
        print("  python foundamental.py run\n")
        return
    
    # Run examples
    try:
        example_1_basic_analysis()
        example_2_brand_specific()
        example_3_temporal_evolution()
        example_4_export_for_visualization()
        example_5_custom_queries()
        
        print("\n" + "="*70)
        print("Demo Complete!")
        print("="*70)
        print("\nTo view the full report, run:")
        print("  python foundamental.py analyze --graph")
        print("\nTo export for visualization:")
        print("  python foundamental.py analyze --export-graph network.json\n")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        print("\nMake sure you have run at least one analysis:")
        print("  python foundamental.py run\n")


if __name__ == "__main__":
    main()
