"""
LLM SEO Analysis Tools
Analyze brand visibility and ranking across different LLM providers
"""
# Import Required Packages
import sqlite3
import json
from collections import defaultdict
import argparse


def get_brand_rankings(db_path="llmseo.db"):
    """Get brand ranking analysis"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('''
        SELECT 
            m.brand_name,
            m.alias_used,
            m.rank_position,
            r.provider_name,
            r.model_name,
            r.query_id,
            m.explanation
        FROM mentions m
        JOIN responses r ON m.response_id = r.id
        ORDER BY m.brand_name, r.provider_name, m.rank_position
    ''')

    mentions = c.fetchall()

    c.execute('SELECT DISTINCT query_id FROM responses WHERE query_id IS NOT NULL')
    query_ids = [row[0] for row in c.fetchall()]

    conn.close()

    try:
        import json
        import os
        config_path = "config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            query_map = {q['id']: q['text'] for q in config['queries']}
        else:
            query_map = {
                1: "Best vector database for RAG",
                2: "Top enterprise chatbots for internal knowledge"
            }
    except:
        query_map = {}

    brand_data = defaultdict(lambda: defaultdict(list))

    for row in mentions:
        brand_name, alias_used, rank, provider, model, query_id, explanation = row
        query_text = query_map.get(query_id, f"Query {query_id}")
        brand_data[brand_name][f"{provider}_{model}"].append({
            'query': query_text,
            'rank': rank,
            'alias_used': alias_used,
            'explanation': explanation
        })

    return dict(brand_data)


def print_brand_report(db_path="llmseo.db"):
    """Print a comprehensive brand visibility report"""
    print("LLM SEO Brand Visibility Report\n" + "="*50)

    brand_data = get_brand_rankings(db_path)

    if not brand_data:
        print("No brand mentions found in database")
        return

    for brand_name, providers in brand_data.items():
        print(f"\n{brand_name}")
        print("-" * (len(brand_name) + 4))

        for provider_model, mentions in providers.items():
            provider, model = provider_model.split("_", 1)
            print(f"\n{provider.upper()} ({model})")

            # Group by query
            query_groups = defaultdict(list)
            for mention in mentions:
                query_groups[mention['query']].append(mention)

            for query, query_mentions in query_groups.items():
                print(f"Query: {query}")
                for mention in sorted(query_mentions, key=lambda x: x['rank']):
                    print(
                        f"      #{mention['rank']} - {mention['alias_used']}")
                    if mention['explanation']:
                        print(f"           {mention['explanation'][:100]}...")


def get_provider_comparison(db_path="llmseo.db"):
    """Compare performance across providers"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('''
        SELECT 
            r.provider_name,
            r.model_name,
            COUNT(DISTINCT m.id) as total_mentions,
            AVG(m.rank_position) as avg_rank,
            COUNT(DISTINCT r.id) as total_responses,
            COUNT(DISTINCT CASE WHEN r.error_message IS NULL THEN r.id END) as successful_responses
        FROM responses r
        LEFT JOIN mentions m ON r.id = m.response_id
        GROUP BY r.provider_name, r.model_name
        ORDER BY total_mentions DESC
    ''')

    results = c.fetchall()
    conn.close()

    return results


def print_provider_comparison(db_path="llmseo.db"):
    """Print provider comparison report"""
    print("\nProvider Performance Comparison\n" + "="*40)

    results = get_provider_comparison(db_path)

    if not results:
        print("No provider data found")
        return

    print(f"{'Provider':<15} {'Model':<15} {'Mentions':<10} {'Avg Rank':<10} {'Success Rate'}")
    print("-" * 70)

    for row in results:
        provider, model, mentions, avg_rank, total_resp, success_resp = row
        success_rate = (success_resp / total_resp *
                        100) if total_resp > 0 else 0
        avg_rank_str = f"{avg_rank:.1f}" if avg_rank else "N/A"

        print(
            f"{provider:<15} {model:<15} {mentions:<10} {avg_rank_str:<10} {success_rate:.1f}%")


def export_to_json(db_path="llmseo.db", output_file="llm_seo_results.json"):
    """Export results to JSON file"""
    brand_data = get_brand_rankings(db_path)
    provider_data = get_provider_comparison(db_path)

    export_data = {
        "brand_rankings": brand_data,
        "provider_performance": [
            {
                "provider": row[0],
                "model": row[1],
                "total_mentions": row[2],
                "avg_rank": row[3],
                "total_responses": row[4],
                "successful_responses": row[5]
            } for row in provider_data
        ]
    }

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"Results exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Analyze LLM SEO results')
    parser.add_argument('--db', default='llmseo.db', help='Database file path')
    parser.add_argument('--export', help='Export to JSON file')
    parser.add_argument('--report', action='store_true',
                        help='Show brand report')
    parser.add_argument('--compare', action='store_true',
                        help='Show provider comparison')

    args = parser.parse_args()

    if args.export:
        export_to_json(args.db, args.export)

    if args.report or (not args.export and not args.compare):
        print_brand_report(args.db)

    if args.compare or (not args.export and not args.report):
        print_provider_comparison(args.db)


if __name__ == "__main__":
    main()
