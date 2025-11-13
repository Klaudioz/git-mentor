"""Token counting using simple heuristics."""

import os
from pathlib import Path

from .logger import setup_logger

logger = setup_logger()

# Gemini 2.5 Pro context window size
# Reference: https://ai.google.dev/gemini-api/docs/models
GEMINI_25_PRO_CONTEXT_WINDOW = 1048576  # 1,048,576 tokens (1M tokens)
WARNING_THRESHOLD = 0.70  # Warn if over 70% of context window

# File extensions to analyze
IMPORTANT_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.h',
    '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh', '.bash',
    '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.css',
    '.sql', '.proto', '.graphql'
}


def estimate_tokens_from_text(text: str) -> int:
    """Estimate token count from text using simple heuristic.

    Args:
        text: Text content to analyze

    Returns:
        Estimated token count
    """
    # Rough estimation: 1 token ≈ 4 characters for English text
    # This is a conservative estimate that works reasonably well
    return len(text) // 4


def count_tokens_for_repo(repo_path: Path) -> dict:
    """Count approximate tokens in a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with token count and analysis
    """
    logger.info(f"Counting tokens for repository: {repo_path}")

    total_tokens = 0
    file_count = 0
    skipped_files = 0

    try:
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue

            # Skip common large directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '__pycache__', '.pytest_cache', 'dist', 'build'}]

            for filename in files:
                file_path = Path(root) / filename

                # Check if file has important extension
                if not any(filename.endswith(ext) for ext in IMPORTANT_EXTENSIONS):
                    skipped_files += 1
                    continue

                # Check file size (skip very large files)
                try:
                    file_size = file_path.stat().st_size
                    if file_size > 1_000_000:  # Skip files over 1MB
                        logger.debug(f"Skipping large file: {file_path} ({file_size:,} bytes)")
                        skipped_files += 1
                        continue

                    # Read and count tokens
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        tokens = estimate_tokens_from_text(content)
                        total_tokens += tokens
                        file_count += 1

                except Exception as e:
                    logger.debug(f"Error reading file {file_path}: {str(e)}")
                    skipped_files += 1
                    continue

        # Calculate percentage of context window
        percentage = (total_tokens / GEMINI_25_PRO_CONTEXT_WINDOW) * 100

        logger.info(f"Repository analysis complete: {file_count:,} files, ~{total_tokens:,} tokens (~{percentage:.2f}% of context window)")
        logger.debug(f"Skipped {skipped_files:,} files")

        return {
            "token_count": total_tokens,
            "file_count": file_count,
            "skipped_files": skipped_files,
            "context_window": GEMINI_25_PRO_CONTEXT_WINDOW,
            "percentage": percentage,
            "exceeds_threshold": percentage > (WARNING_THRESHOLD * 100),
            "threshold": WARNING_THRESHOLD * 100,
        }

    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}", exc_info=True)
        return {
            "token_count": 0,
            "file_count": 0,
            "skipped_files": 0,
            "context_window": GEMINI_25_PRO_CONTEXT_WINDOW,
            "percentage": 0,
            "exceeds_threshold": False,
            "threshold": WARNING_THRESHOLD * 100,
            "error": str(e),
        }


def should_warn_about_size(repo_path: Path) -> tuple[bool, str]:
    """Check if repository is too large and return warning message.

    Args:
        repo_path: Path to the repository

    Returns:
        Tuple of (should_warn, warning_message)
    """
    stats = count_tokens_for_repo(repo_path)

    if "error" in stats:
        logger.warning(f"Could not analyze repository size: {stats['error']}")
        return False, ""

    if stats["exceeds_threshold"]:
        message = f"""⚠️  Warning: Large Repository

This repository is approximately {stats['percentage']:.1f}% of the AI model's context window.

Files analyzed: {stats['file_count']:,}
Estimated tokens: ~{stats['token_count']:,}
Threshold: {stats['threshold']:.0f}%

Large repositories may:
- Take longer to analyze
- Cost more to process
- Produce less detailed analysis

Recommendation: Start with smaller repositories (10-50 commits, <1000 files) for optimal learning experience."""

        logger.warning(f"Repository exceeds size threshold: {stats['percentage']:.1f}% ({stats['file_count']} files)")
        return True, message

    logger.info(f"Repository size is acceptable: {stats['percentage']:.1f}% ({stats['file_count']} files)")
    return False, ""
