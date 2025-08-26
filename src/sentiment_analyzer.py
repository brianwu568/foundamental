#!/usr/bin/env python3
"""
Brand Sentiment Analyzer
Analyze sentiment of brand mentions in LLM responses using BAML
"""

import asyncio
import sqlite3
from baml_client import b


async def analyze_brand_sentiment(db_path="llmseo.db"):
    """Analyze sentiment for all brand mentions in the database"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT m.id, m.brand_name, m.explanation, m.alias_used
        FROM mentions m
        WHERE m.explanation IS NOT NULL AND m.explanation != ""
    ''')
    
    mentions = c.fetchall()
    
    if not mentions:
        print("No mentions with explanations found")
        return
    
    print(f"Analyzing sentiment for {len(mentions)} brand mentions...")

    try:
        c.execute('ALTER TABLE mentions ADD COLUMN sentiment TEXT')
        c.execute('ALTER TABLE mentions ADD COLUMN sentiment_confidence REAL')
    except sqlite3.OperationalError:
        pass # Columns already exist
    
    results = []
    for mention_id, brand_name, explanation, alias_used in mentions:
        try:
            sentiment_result = b.BrandSentiment(
                brand=brand_name,
                passage=explanation
            )
            
            c.execute('''
                UPDATE mentions 
                SET sentiment = ?, sentiment_confidence = ?
                WHERE id = ?
            ''', (sentiment_result.sentiment.value, sentiment_result.confidence, mention_id))
            
            results.append({
                'brand': brand_name,
                'alias': alias_used,
                'sentiment': sentiment_result.sentiment.value,
                'confidence': sentiment_result.confidence,
                'explanation': explanation[:100] + "..." if len(explanation) > 100 else explanation
            })
            
            print(f"{brand_name} ({alias_used}): {sentiment_result.sentiment.value} ({sentiment_result.confidence:.2f})")
            
        except Exception as e:
            print(f"Error analyzing {brand_name}: {e}")
    
    conn.commit()
    conn.close()
    
    return results


def print_sentiment_report(db_path="llmseo.db"):
    """Print sentiment analysis report"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            brand_name,
            sentiment,
            AVG(sentiment_confidence) as avg_confidence,
            COUNT(*) as mention_count
        FROM mentions 
        WHERE sentiment IS NOT NULL
        GROUP BY brand_name, sentiment
        ORDER BY brand_name, mention_count DESC
    ''')
    
    results = c.fetchall()
    conn.close()
    
    if not results:
        print("No sentiment data found. Run analyze_brand_sentiment first.")
        return
    
    print("\nBrand Sentiment Analysis Report")
    print("=" * 50)
    
    current_brand = None
    for brand_name, sentiment, avg_confidence, mention_count in results:
        if brand_name != current_brand:
            if current_brand is not None:
                print()
            print(f"{brand_name}")
            print("-" * (len(brand_name) + 4))
            current_brand = brand_name
        print(f"{sentiment}: {mention_count} mentions (avg confidence: {avg_confidence:.2f})")


async def main():
    """Main function for sentiment analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze brand sentiment in LLM responses')
    parser.add_argument('--db', default='llmseo.db', help='Database file path')
    parser.add_argument('--analyze', action='store_true', help='Run sentiment analysis')
    parser.add_argument('--report', action='store_true', help='Show sentiment report')
    
    args = parser.parse_args()
    
    if args.analyze or (not args.report):
        await analyze_brand_sentiment(args.db)
    
    if args.report or (not args.analyze):
        print_sentiment_report(args.db)


if __name__ == "__main__":
    asyncio.run(main())
