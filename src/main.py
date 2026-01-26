"""
Gold-Silver-Intelligence Main Entry Point
Runs the AgentScope pipeline and sends reports via Telegram.
"""
import argparse
import sys

# Add project root to path for imports
sys.path.insert(0, ".")

from src.agents import run_analysis_pipeline
from src.telegram_bot import send_report


def main():
    """Main entry point for the Gold-Silver Intelligence Agent."""
    parser = argparse.ArgumentParser(
        description="Gold-Silver Intelligence Agent - Market News Analyzer"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="gold silver price news Fed interest rate",
        help="Search query for news (default: gold silver price news)"
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Skip sending report to Telegram"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("🥇 Gold-Silver Intelligence Agent")
    print("=" * 50)

    try:
        # Run analysis pipeline
        report = run_analysis_pipeline(args.query)

        print("\n" + "=" * 50)
        print("📊 ANALYSIS REPORT")
        print("=" * 50)
        print(report)

        # Send to Telegram
        if not args.no_telegram:
            print("\n[INFO] Sending report to Telegram...")
            success = send_report(
                title="Gold-Silver Intelligence Report",
                content=report
            )
            if success:
                print("[OK] Report sent to Telegram successfully!")
            else:
                print("[WARN] Failed to send report to Telegram.")

        print("\n✅ Analysis completed.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
