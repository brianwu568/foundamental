# Import Required Packages
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from sentiment_analyzer import main as sentiment_analysis
from analyze import main as analyze_results
from run import main as run_analysis
from run_with_sources import main as run_analysis_with_sources
from hallucination_filter import main as hallucination_analysis
from competitor_graph import main as competitor_graph_analysis
import argparse
import asyncio

def main():
    parser = argparse.ArgumentParser(
        description='LLM SEO Brand Visibility Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run                        # Run brand analysis
  %(prog)s run --with-sources         # Run with hallucination filter
  %(prog)s analyze --report           # View brand report  
  %(prog)s analyze --compare          # Compare providers
  %(prog)s analyze --graph            # View competitor graph
  %(prog)s analyze --graph --brand YourBrand  # Competitor analysis for specific brand
  %(prog)s analyze --export out.json  # Export to JSON
  %(prog)s analyze --export-graph graph.json  # Export competitor graph to JSON
  %(prog)s sentiment --analyze        # Analyze brand sentiment
  %(prog)s hallucination --analyze    # Analyze hallucination risks
  %(prog)s hallucination --report     # View hallucination report
        """)

    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    run_parser = subparsers.add_parser(
        'run', help='Run brand visibility analysis')
    run_parser.add_argument(
        '--config', default='config.json', help='Config file path')
    run_parser.add_argument(
        '--with-sources', action='store_true', 
        help='Enable hallucination filter (request sources and confidence)')

    analyze_parser = subparsers.add_parser('analyze', help='Analyze results')
    analyze_parser.add_argument(
        '--db', default='llmseo.db', help='Database file path')
    analyze_parser.add_argument('--export', help='Export to JSON file')
    analyze_parser.add_argument(
        '--report', action='store_true', help='Show brand report')
    analyze_parser.add_argument(
        '--compare', action='store_true', help='Show provider comparison')
    analyze_parser.add_argument(
        '--graph', action='store_true', help='Show competitor graph analysis')
    analyze_parser.add_argument(
        '--brand', type=str, help='Focus graph analysis on specific brand')
    analyze_parser.add_argument(
        '--export-graph', type=str, help='Export competitor graph to JSON file')
    analyze_parser.add_argument(
        '--min-strength', type=float, default=0.0,
        help='Minimum relationship strength for graph (0.0-1.0)')

    sentiment_parser = subparsers.add_parser(
        'sentiment', help='Analyze brand sentiment')
    sentiment_parser.add_argument(
        '--db', default='llmseo.db', help='Database file path')
    sentiment_parser.add_argument(
        '--analyze', action='store_true', help='Run sentiment analysis')
    sentiment_parser.add_argument(
        '--report', action='store_true', help='Show sentiment report')
    
    hallucination_parser = subparsers.add_parser(
        'hallucination', help='Hallucination filter analysis')
    hallucination_parser.add_argument(
        '--db', default='llmseo.db', help='Database file path')
    hallucination_parser.add_argument(
        '--analyze', action='store_true', help='Run hallucination analysis')
    hallucination_parser.add_argument(
        '--report', action='store_true', help='Show hallucination report')
    hallucination_parser.add_argument(
        '--verify-urls', action='store_true', 
        help='Verify URL accessibility (slower)')

    args = parser.parse_args()

    if args.command == 'run':
        mode_str = "with hallucination filter" if args.with_sources else ""
        print(f"Starting LLM SEO brand analysis {mode_str}...")
        try:
            if args.with_sources:
                asyncio.run(run_analysis_with_sources(with_sources=True))
            else:
                asyncio.run(run_analysis())
        except KeyboardInterrupt:
            print("\n Analysis interrupted by user")
        except Exception as e:
            print(f"Error during analysis: {e}")

    elif args.command == 'analyze':
        # Handle competitor graph analysis
        if args.graph or args.export_graph:
            graph_args = ['competitor_graph.py']
            if args.db != 'llmseo.db':
                graph_args.extend(['--db', args.db])
            if args.export_graph:
                graph_args.extend(['--export', args.export_graph])
                if args.min_strength > 0.0:
                    graph_args.extend(['--min-strength', str(args.min_strength)])
            else:
                graph_args.append('--report')
                if args.brand:
                    graph_args.extend(['--brand', args.brand])
            
            original_argv = sys.argv
            sys.argv = graph_args
            try:
                competitor_graph_analysis()
            finally:
                sys.argv = original_argv
        else:
            # Standard analysis
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
    
    elif args.command == 'hallucination':
        hallucination_args = ['hallucination_filter.py']
        if args.db != 'llmseo.db':
            hallucination_args.extend(['--db', args.db])
        if args.analyze:
            hallucination_args.append('--analyze')
        if args.report:
            hallucination_args.append('--report')
        if args.verify_urls:
            hallucination_args.append('--verify-urls')

        original_argv = sys.argv
        sys.argv = hallucination_args
        try:
            asyncio.run(hallucination_analysis())
        finally:
            sys.argv = original_argv

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
