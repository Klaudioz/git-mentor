"""Entry point for Commit Teacher - allows running with 'python main.py'."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from commit_teacher.main import main

if __name__ == "__main__":
    main()
