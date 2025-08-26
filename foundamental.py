# Import Required Packages
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from run import main as run_analysis
from analyze import main as analyze_results
from sentiment_analyzer import main as sentiment_analysis


def main():
    parser = argparse.ArgumentParser(
        description='LLM SEO Brand Visibility Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run                        # Run brand analysis
  %(prog)s analyze --report           # View brand report  
  %(prog)s analyze --compare          # Compare providers
  %(prog)s analyze --export out.json  # Export to JSON
  %(prog)s sentiment --analyze        # Analyze brand sentiment
        """)
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    run_parser = subparsers.add_parser('run', help='Run brand visibility analysis')
    run_parser.add_argument('--config', default='config.json', help='Config file path')
    
    analyze_parser = subparsers.add_parser('analyze', help='Analyze results')
    analyze_parser.add_argument('--db', default='llmseo.db', help='Database file path')
    analyze_parser.add_argument('--export', help='Export to JSON file')
    analyze_parser.add_argument('--report', action='store_true', help='Show brand report')
    analyze_parser.add_argument('--compare', action='store_true', help='Show provider comparison')
    
    sentiment_parser = subparsers.add_parser('sentiment', help='Analyze brand sentiment')
    sentiment_parser.add_argument('--db', default='llmseo.db', help='Database file path')
    sentiment_parser.add_argument('--analyze', action='store_true', help='Run sentiment analysis')
    sentiment_parser.add_argument('--report', action='store_true', help='Show sentiment report')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        print("Starting LLM SEO brand analysis...")
        try:
            asyncio.run(run_analysis())
        except KeyboardInterrupt:
            print("\nAnalysis interrupted by user")
        except Exception as e:
            print(f"Error during analysis: {e}")
    
    elif args.command == 'analyze':
        analyze_args = ['analyze.py']
        if args.db != 'llmseo.db':
            analyze_args.extend(['--db', args.db])
        if args.export:
            analyze_args.extend(['--export', args.export])
        if args.report:
            analyze_args.append('--report')
        if args.compare:
            analyze_args.append('--compare')
    
        original_argv = sys.argv
        sys.argv = analyze_args
        try:
            analyze_results()
        finally:
            sys.argv = original_argv
    
    elif args.command == 'sentiment':
        sentiment_args = ['sentiment_analyzer.py']
        if args.db != 'llmseo.db':
            sentiment_args.extend(['--db', args.db])
        if args.analyze:
            sentiment_args.append('--analyze')
        if args.report:
            sentiment_args.append('--report')
        
        original_argv = sys.argv
        sys.argv = sentiment_args
        try:
            asyncio.run(sentiment_analysis())
        finally:
            sys.argv = original_argv
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
