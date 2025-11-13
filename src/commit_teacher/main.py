"""Main entry point for Commit Teacher."""

import argparse
import sys

from .ui.app import CommitTeacherApp


def parse_args():
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Commit Teacher - Learn code by walking through Git commit history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with interactive setup
  python main.py

  # Load a specific repository
  python main.py --repo https://github.com/badlogic/pi-mono

  # Load repository and skip cache (fresh analysis)
  python main.py --repo https://github.com/pallets/click --no-cache

  # Resume from last position
  python main.py --repo https://github.com/badlogic/pi-mono --resume
        """
    )

    parser.add_argument(
        "--repo",
        "-r",
        type=str,
        help="GitHub repository URL to analyze (e.g., https://github.com/owner/repo)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache and perform fresh analysis (slower, uses more API calls)"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last viewed commit (default behavior if cache exists)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Commit Teacher 0.1.0"
    )

    return parser.parse_args()


def main():
    """Run the Commit Teacher application."""
    args = parse_args()

    try:
        app = CommitTeacherApp(
            initial_repo=args.repo,
            use_cache=not args.no_cache,
            auto_resume=args.resume
        )
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
