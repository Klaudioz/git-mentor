"""Code architecture analyzer using AI."""

import os
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from .logger import setup_logger

load_dotenv()

logger = setup_logger()


class CodeAnalyzer:
    """Analyzes code architecture and changes using AI."""

    def __init__(self):
        """Initialize code analyzer with Gemini API."""
        logger.info("Initializing CodeAnalyzer")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        logger.info(f"Using Gemini model: {model_name}")
        self.model = genai.GenerativeModel(model_name)

    def analyze_initial_architecture(self, file_tree: list[str], file_contents: dict[str, str]) -> str:
        """Analyze the initial architecture of the codebase.

        Args:
            file_tree: List of all files in the repository
            file_contents: Dictionary mapping file paths to their contents

        Returns:
            Architecture analysis as markdown
        """
        logger.info(f"Analyzing initial architecture with {len(file_tree)} files")
        logger.debug(f"Analyzing contents of {len(file_contents)} files")

        files_text = "\n\n".join([
            f"File: {path}\n```\n{content}\n```"
            for path, content in file_contents.items()
        ])

        prompt = f"""Analyze this codebase and provide a comprehensive architecture overview. This is the first commit of the project.

Files in repository:
{', '.join(file_tree)}

File contents:
{files_text}

Please provide:
1. Project structure overview
2. Key components and their responsibilities
3. Main technologies and frameworks used
4. Entry points and main workflows
5. Important patterns or architectural decisions

Format your response as a clear, educational markdown document that helps someone understand the codebase structure."""

        try:
            logger.info("Sending initial architecture analysis request to Gemini API")
            response = self.model.generate_content(prompt)
            logger.info("Successfully received architecture analysis from Gemini API")
            return response.text

        except Exception as e:
            logger.error(f"Error analyzing initial architecture: {str(e)}", exc_info=True)
            return f"Error analyzing architecture: {str(e)}"

    def analyze_commit_changes(
        self,
        commit_stats: dict,
        diff: Optional[str],
        current_architecture: str
    ) -> tuple[str, Optional[str]]:
        """Analyze changes in a commit and provide educational explanation.

        Args:
            commit_stats: Statistics about the commit
            diff: Git diff of the changes
            current_architecture: Current architecture documentation

        Returns:
            Tuple of (explanation, updated_architecture)
            updated_architecture is None if no update is needed
        """
        commit_sha = commit_stats.get('sha', 'unknown')
        logger.info(f"Analyzing commit changes for {commit_sha}")

        if not diff:
            logger.warning("No diff available for commit analysis")
            return "This is the first commit with no previous changes to compare.", None

        files_changed = commit_stats.get('files_changed', [])
        logger.debug(f"Commit {commit_sha} changed {len(files_changed)} files")

        prompt = f"""Analyze this commit and explain the changes in an educational way.

Commit Information:
- SHA: {commit_stats.get('sha', 'unknown')}
- Author: {commit_stats.get('author', 'unknown')}
- Date: {commit_stats.get('date', 'unknown')}
- Message: {commit_stats.get('message', 'No message')}

Files changed:
{self._format_files_changed(files_changed)}

Diff:
```
{diff[:10000]}
```

Current Architecture:
{current_architecture}

Please provide:
1. What changed - Summary of the modifications
2. Why it matters - Educational explanation of the purpose and impact
3. Key concepts - Any programming concepts or patterns introduced
4. Architecture impact - Does this change affect the architecture? (YES/NO)

If the architecture is affected, provide an updated architecture document. Otherwise, state "NO ARCHITECTURE UPDATE NEEDED".

Format your response as:
## What Changed
[summary]

## Why It Matters
[explanation]

## Key Concepts
[concepts]

## Architecture Impact
[YES/NO and explanation]

## Updated Architecture (if needed)
[updated architecture document or "NO ARCHITECTURE UPDATE NEEDED"]"""

        try:
            logger.info(f"Sending commit analysis request to Gemini API for {commit_sha}")
            response = self.model.generate_content(prompt)
            response_text = response.text
            logger.info(f"Successfully received commit analysis for {commit_sha}")

            updated_arch = None
            if "## Updated Architecture" in response_text:
                arch_section = response_text.split("## Updated Architecture")[1].strip()
                if "NO ARCHITECTURE UPDATE NEEDED" not in arch_section:
                    updated_arch = arch_section
                    logger.info(f"Architecture update detected for commit {commit_sha}")
                else:
                    logger.debug(f"No architecture update needed for commit {commit_sha}")

            return response_text, updated_arch

        except Exception as e:
            logger.error(f"Error analyzing commit {commit_sha}: {str(e)}", exc_info=True)
            return f"Error analyzing commit: {str(e)}", None

    def answer_question(self, question: str, context: dict) -> str:
        """Answer a user question about the codebase.

        Args:
            question: User's question
            context: Dictionary with current context (architecture, commit info, etc.)

        Returns:
            Answer to the question
        """
        logger.info(f"Answering user question: {question[:100]}...")

        context_text = f"""Current Context:

Architecture:
{context.get('architecture', 'No architecture available')}

Current Commit:
- SHA: {context.get('commit_sha', 'unknown')}
- Message: {context.get('commit_message', 'unknown')}
- Files changed: {', '.join([f['path'] for f in context.get('files_changed', [])])}

Recent Explanation:
{context.get('last_explanation', 'No recent explanation')}
"""

        prompt = f"""{context_text}

User Question: {question}

Please provide a clear, educational answer to the user's question based on the context above. If you need more information, explain what additional context would be helpful."""

        try:
            logger.debug("Sending Q&A request to Gemini API")
            response = self.model.generate_content(prompt)
            logger.info("Successfully received answer from Gemini API")
            return response.text

        except Exception as e:
            logger.error(f"Error answering question: {str(e)}", exc_info=True)
            return f"Error answering question: {str(e)}"

    def _format_files_changed(self, files_changed: list[dict]) -> str:
        """Format files changed for prompt.

        Args:
            files_changed: List of file change dictionaries

        Returns:
            Formatted string
        """
        if not files_changed:
            return "No files changed"

        lines = []
        for file in files_changed:
            lines.append(f"- {file['path']} ({file['type']})")

        return "\n".join(lines)
