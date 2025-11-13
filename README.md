# Commit Teacher

An interactive terminal application that helps you learn code by walking through Git commit history. Using AI-powered analysis, it explains what changed in each commit, why it matters, and how it affects the overall architecture.

## Features

- **Chronological Learning**: Walk through repository history from first commit to latest
- **AI-Powered Explanations**: Understand what changed, why it matters, and key concepts
- **Architecture Tracking**: Automatically maintains and updates architecture documentation
- **Interactive Q&A**: Ask questions about the code at any point
- **Beautiful TUI**: Modern terminal interface built with Textual
- **Large Context Analysis**: Uses Google Gemini for its extensive context window (1M tokens), allowing analysis of large codebases and complete commit histories
- **GitHub Integration**: Clickable commit SHAs that open directly in your browser
- **Smart Caching**: Instantly resume sessions and navigate through previously analyzed commits

### What You'll Learn
- How projects evolve organically
- Design patterns in real codebases
- Why certain architectural decisions were made
- Programming concepts in context
- Code review and analysis skills

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Git installed on your system
- Google Gemini API key

### Installation

1. **Clone this repository**
```bash
git clone <your-repo-url>
cd commit-teacher
```

2. **Create a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure your API key**
```bash
cp .env.example .env
```

Edit `.env` and add your Google Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

**Get your API key (choose one method):**

**Option 1: Google AI Studio (Fastest - Free tier available)**
- Visit: https://aistudio.google.com/app/apikey
- Click "Create API Key"
- Copy the generated key

**Option 2: Google Cloud Platform (GCP - For production use)**
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project or select an existing one
- Enable the "Generative Language API":
  - Navigate to "APIs & Services" > "Library"
  - Search for "Generative Language API"
  - Click "Enable"
- Create an API key:
  - Go to "APIs & Services" > "Credentials"
  - Click "Create Credentials" > "API Key"
  - Copy the generated key
  - (Optional) Restrict the key to "Generative Language API" for security

5. **Run the application**
```bash
# Interactive mode (with setup screen)
python main.py

# Or use the module path
python -m src.commit_teacher.main

# Direct mode (skip setup, load repository immediately)
python main.py --repo https://github.com/badlogic/pi-mono
```

## Usage

### Command-Line Options

```bash
# Interactive mode - shows setup screen
python main.py

# Load a specific repository directly
python main.py --repo https://github.com/owner/repo

# Skip cache and perform fresh analysis (uses more API calls)
python main.py --repo https://github.com/owner/repo --no-cache

# Force resume from last position
python main.py --repo https://github.com/owner/repo --resume

# View help and all options
python main.py --help
```

### First Run

1. Enter a GitHub repository URL (start with small repos: 10-50 commits)
   - Example: `https://github.com/pallets/click`
   - Example: `https://github.com/kennethreitz/requests`

2. Wait for initial analysis (1-2 minutes for first commit)

3. Navigate through commits using keyboard shortcuts

### Keyboard Shortcuts

- `n` - Navigate to next commit
- `p` - Navigate to previous commit
- `d` - Show git diff for current commit
- `c` - Open chat interface to ask questions
- `escape` - Close chat and return to commit view
- `q` - Quit application

**Tip:** Click on the commit SHA to open it in your browser on GitHub!

### Learning Workflow

```
1. Enter Repository URL
   ↓
2. Review Initial Architecture
   ↓
3. Press 'n' to Next Commit
   ↓
4. Read AI Explanation:
   • What Changed
   • Why It Matters
   • Key Concepts
   • Architecture Impact
   ↓
5. Press 'c' to Ask Questions
   ↓
6. Continue to Next Commit
```

### Example Sessions

**Interactive Mode:**
```bash
# Start the app
python main.py

# Enter URL: https://github.com/pallets/click
# Wait for analysis...
# Read architecture overview
# Press 'n' to see next commit
# Read explanation of changes
# Press 'c' to ask: "What design pattern is being used here?"
# Continue learning!
```

**Direct Mode:**
```bash
# Load repository directly from command line
python main.py --repo https://github.com/pallets/click

# Skip straight to first commit
# No URL input required
# Cache automatically resumes from last position if available
```

**Fresh Analysis (No Cache):**
```bash
# Analyze from scratch, ignoring any cached data
python main.py --repo https://github.com/pallets/click --no-cache

# Useful when you want to see updated AI analysis
# or if cache seems corrupted
```

## Troubleshooting

### "GEMINI_API_KEY not found"
Make sure you've created a `.env` file in the project root and added your API key:
```bash
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here
```

### "No module named 'google.generativeai'"
Install the dependencies:
```bash
pip install -r requirements.txt
```

### Repository cloning fails
- Ensure the URL is correct and accessible
- Check your network connection
- Private repositories require authentication

### Slow analysis
- AI analysis takes time, especially for large commits
- The first commit is the slowest (full architecture analysis)
- Consider starting with smaller repositories (10-50 commits)

### Import errors
Make sure you're running from the project root:
```bash
cd /path/to/commit-teacher
python -m src.commit_teacher.main
```

## Tips for Best Experience

1. **Start Small**: Choose repositories with 10-50 commits for your first try
2. **Read Thoroughly**: Take time to read each explanation before moving forward
3. **Ask Questions**: Use the chat feature liberally to explore concepts
4. **Review Architecture**: Periodically check the generated `.architecture.md` file
5. **Take Notes**: Document interesting patterns and insights you discover
6. **Compare Commits**: Think about how each change builds on previous ones

## Configuration

### Environment Variables

- `GEMINI_API_KEY` (required): Your Google Gemini API key
- `GEMINI_MODEL` (optional): Model to use (default: `gemini-2.5-pro`)

### Generated Files

- `repos/<repo-name>/` - Cloned repository
- `<repo-name>.architecture.md` - Architecture documentation

### Limitations

- First 20 files analyzed for initial architecture (to manage API costs)
- Files over 10KB are skipped in analysis
- Diffs are truncated to 10,000 characters for processing
- Large repositories (100+ commits) take longer to process

## Why Google Gemini?

This project uses Google Gemini API for several key reasons:

- **Massive Context Window**: Gemini 2.5 Pro supports up to 1,048,576 input tokens, allowing analysis of entire codebases and long commit histories without truncation
- **Code Understanding**: Excellent performance on code analysis and architectural reasoning tasks
- **Cost Effective**: Competitive pricing for educational and learning use cases
- **Free Tier Available**: Google AI Studio offers free API access for development and learning

The large context window is critical for understanding how commits relate to the overall architecture and maintaining consistency across the entire codebase analysis.

Reference: [Gemini API Models](https://ai.google.dev/gemini-api/docs/models)

## Philosophy

This tool is designed around how humans naturally learn:

- **Context First**: Understand the foundation before exploring changes
- **Incremental Growth**: See how codebases evolve step by step
- **Active Learning**: Ask questions when curious
- **Pattern Recognition**: Identify recurring techniques and patterns
- **Real Examples**: Learn from actual production code

By walking through commits chronologically, you experience the thought process of the original developers and understand **why** code exists, not just **what** it does.

## Resources

- [Textual Documentation](https://textual.textualize.io/) - TUI framework
- [GitPython Documentation](https://gitpython.readthedocs.io/) - Git integration
- [Google Gemini API Documentation](https://ai.google.dev/docs) - AI provider
- [Google AI Studio](https://aistudio.google.com/) - Get API keys

## Contributing

Contributions are welcome! The modular architecture makes it easy to:
- Add new AI analyzers
- Create new TUI screens
- Extend Git operations
- Add new storage formats

See `CLAUDE.md` for technical architecture details.

## License

MIT

---

**Learn by walking through history, one commit at a time.**
