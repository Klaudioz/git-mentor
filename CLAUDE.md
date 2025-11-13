# Commit Teacher - Technical Overview

Educational TUI application for learning code through chronological commit analysis using AI.

## Architecture

### Project Structure
```
src/commit_teacher/
├── main.py              # Entry point
├── git_handler.py       # Git operations (clone, navigate, diff)
├── analyzer.py          # AI analysis (Gemini API)
├── storage.py           # Architecture documentation storage
├── cache.py             # Commit analysis caching and session resume
└── ui/
    ├── app.py           # Main TUI orchestrator
    └── screens/
        ├── setup.py     # Repository input screen
        ├── commit.py    # Commit viewing screen
        └── chat.py      # Q&A interface
```

### Key Modules

**git_handler.py**
- Clones repositories to `repos/` directory
- Navigates commits chronologically (oldest first)
- Generates diffs between commits (raw and formatted with ANSI colors)
- Provides file tree and content access
- Generates GitHub commit URLs for browser integration
- Methods: `clone_repository()`, `go_to_first_commit()`, `go_to_next_commit()`, `go_to_previous_commit()`, `get_commit_diff()`, `get_commit_diff_formatted()`, `get_commit_url()`

**analyzer.py**
- Uses Google Gemini API (`gemini-2.5-pro` model)
- Analyzes initial architecture from first commit
- Explains each commit educationally (what, why, concepts, impact)
- Detects and updates architecture changes
- Provides contextual Q&A
- Methods: `analyze_initial_architecture()`, `analyze_commit_changes()`, `answer_question()`

**storage.py**
- Saves architecture as `<repo-name>.architecture.md`
- Loads and updates documentation as code evolves
- Provides persistent learning context
- Methods: `save_architecture()`, `load_architecture()`, `update_architecture()`

**cache.py**
- Stores AI-generated commit analyses in JSON format
- Enables session resumption from last viewed commit
- Tracks cache coverage and statistics
- Saves position in commit history
- Methods: `load_cache()`, `save_commit_analysis()`, `get_commit_analysis()`, `save_last_position()`, `get_cache_stats()`

**ui/app.py**
- Main Textual application orchestrator
- Manages three screens: Setup, Commit, Chat
- Coordinates Git, AI, storage, and cache components
- Handles async operations and user interactions
- Message-based communication between screens

### Data Flow

```
User Input (GitHub URL)
  → GitHandler.clone_repository()
  → CacheHandler.load_cache(repo_name)  # Load existing cache or create new
  → GitHandler.go_to_first_commit()
  → CacheHandler.update_total_commits()  # Check for new commits
  → Check if should resume from last position
    ├─ If resuming: Load cached explanations and navigate to last position
    └─ If not resuming: Analyze first commit
  → CacheHandler.get_commit_analysis(sha)  # Check cache
    ├─ If cached: Use cached explanation (instant, no API call)
    └─ If not cached: CodeAnalyzer.analyze_initial_architecture()
       → CacheHandler.save_commit_analysis()
       → StorageHandler.save_architecture(doc)
  → CacheHandler.save_last_position()
  → CommitScreen displays initial state with cache status

User Navigation ('n' key)
  → GitHandler.go_to_next_commit()
  → CacheHandler.get_commit_analysis(sha)  # Check cache first
    ├─ If cached: Use cached explanation (instant, no API call)
    └─ If not cached:
       → GitHandler.get_commit_diff()
       → GitHandler.get_commit_stats()
       → CodeAnalyzer.analyze_commit_changes(stats, diff, architecture)
       → CacheHandler.save_commit_analysis()
       → StorageHandler.update_architecture(updated_doc) [if needed]
  → CacheHandler.save_last_position()
  → CommitScreen updates with explanation and cache indicator

User Views Cache Info ('i' key)
  → CacheHandler.get_cache_stats()
  → Display cache coverage, position, and statistics

User Question ('c' key, input)
  → Gather context: {architecture, commit_info, recent_explanation}
  → CodeAnalyzer.answer_question(question, context)
  → ChatScreen displays answer
  (Note: Q&A responses are not cached)
```

## Configuration

### File Organization

The application maintains a clean workspace structure:

```
commit-teacher/
├── repos/              # Cloned repositories (managed by GitHandler)
│   └── <repo-name>/    # Each repository in its own directory
├── data/               # Application data (architecture docs, cache)
│   ├── <repo-name>.architecture.md
│   └── <repo-name>.cache.json
└── logs/               # Application logs (timestamped)
    └── commit_teacher_YYYYMMDD_HHMMSS.log
```

**Design Principles:**
- All generated files are organized in dedicated directories
- No files created in current working directory (CWD)
- Easy to locate and manage application data
- Consistent with standard application structure

**Directory Management:**
- `repos/` - Created by GitHandler on initialization
- `data/` - Created by StorageHandler and CacheHandler on initialization
- `logs/` - Created by logging configuration on startup
- All directories use `mkdir(exist_ok=True)` for idempotency

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
GEMINI_MODEL=gemini-2.5-pro  # default
```

### Generated Files and Directories
- `repos/` - Cloned repositories working directory
  - `repos/<repo-name>/` - Individual repository clone
- `data/` - Application data directory
  - `data/<repo-name>.architecture.md` - Living architecture document
  - `data/<repo-name>.cache.json` - Cached commit analyses and session state
- `logs/` - Application logs directory
  - `logs/commit_teacher_YYYYMMDD_HHMMSS.log` - Application logs (DEBUG level, timestamped)

### Cache File Structure
The cache file stores commit analyses in JSON format:
```json
{
  "repo_name": "my-project",
  "repo_url": "https://github.com/user/repo",
  "last_commit_index": 5,
  "total_commits": 42,
  "cache_version": "1.0",
  "created_at": "2025-11-12T10:30:00",
  "commits": {
    "abc1234": {
      "sha": "abc1234",
      "explanation": "## What Changed\n...",
      "architecture_version": null,
      "analyzed_at": "2025-11-12T10:35:00",
      "cached": true
    }
  }
}
```

Benefits:
- **Cost Reduction**: Avoid redundant API calls for previously analyzed commits
- **Speed**: Instant loading of cached explanations (no API wait time)
- **Session Continuity**: Resume from last viewed commit automatically
- **Transparency**: UI shows cache status ([CACHED] vs [ANALYZED]) for each commit

### Processing Limits
To manage API costs and performance:
- **Repository Size Check**: Estimates tokens using character count heuristic (1 token ≈ 4 chars)
- **Size Warning**: Warns if repository exceeds 70% of Gemini's context window (1,048,576 tokens)
- First 20 files analyzed for initial architecture
- Files over 10KB skipped in analysis
- Diffs truncated to 10,000 characters
- Only important file extensions analyzed (.py, .js, .ts, .java, .go, .rs, .md, etc.)

### Repository Size Checking
The application uses a simple heuristic to estimate token count:
```python
from .token_counter import should_warn_about_size, estimate_tokens_from_text

# Estimation method: 1 token ≈ 4 characters
def estimate_tokens_from_text(text: str) -> int:
    return len(text) // 4

# After cloning
should_warn, message = should_warn_about_size(repo_path)
if should_warn:
    # Display warning to user
    logger.warning(f"Repository exceeds threshold: {message}")
```

Token estimation helps avoid:
- Expensive API calls on oversized repositories
- Poor analysis quality from context overflow
- Long processing times

Excluded from analysis:
- `.git`, `node_modules`, `venv`, `__pycache__`, `.pytest_cache`, `dist`, `build`
- Files over 1MB
- Non-code files (images, binaries, etc.)

Recommended repository characteristics for learning:
- 10-50 commits
- Under 1,000 files
- <70% of context window (~734K tokens)

## Logging

### Configuration
Logging is automatically configured when the application starts:
- **Log File**: `logs/commit_teacher_YYYYMMDD_HHMMSS.log` (timestamped, new file per run)
- **Console**: Only warnings and errors printed to stderr
- **Format**: Timestamp, module, level, location, message

### Log Levels
- **DEBUG**: Detailed information (file contents, API calls)
- **INFO**: Key operations (cloning, navigation, API requests)
- **WARNING**: Non-critical issues (already at latest commit, etc.)
- **ERROR**: Errors with stack traces

### Example Log Output
```
2025-11-12 19:45:23 - commit_teacher - INFO - [app.py:34] - Initializing CommitTeacherApp
2025-11-12 19:45:23 - commit_teacher - INFO - [git_handler.py:31] - Initialized GitHandler with workspace: repos
2025-11-12 19:45:45 - commit_teacher - INFO - [git_handler.py:42] - Attempting to clone repository: https://github.com/user/repo
2025-11-12 19:46:12 - commit_teacher - INFO - [analyzer.py:68] - Sending initial architecture analysis request to Gemini API
```

### Viewing Logs
```bash
# View the latest log file
tail -f logs/commit_teacher_*.log

# List all log files
ls -lt logs/

# View errors only from latest log
grep ERROR logs/commit_teacher_$(ls -t logs/ | head -1)

# View specific module from latest log
grep "git_handler" logs/commit_teacher_$(ls -t logs/ | head -1)

# Clean old logs (keep last 10)
cd logs && ls -t | tail -n +11 | xargs rm -f
```

## Development

### Dependencies
```python
textual>=0.50.0              # Modern TUI framework
gitpython>=3.1.40            # Git operations
google-generativeai>=0.3.0   # Gemini API
python-dotenv>=1.0.0         # Environment config
rich>=13.7.0                 # Terminal formatting
```

Notes:
- Token counting uses a simple character-based heuristic (no external dependencies)
- Diff formatting uses custom ANSI color codes for syntax highlighting

### Extension Points

**Adding New Analyzers**
Extend `analyzer.py` with new analysis methods:
```python
def analyze_security_issues(self, code: str) -> dict:
    # Custom analysis logic
    pass
```

**Creating New Screens**
Add screens in `ui/screens/`:
```python
from textual.screen import Screen

class NewScreen(Screen):
    def compose(self):
        # Define widgets
        pass
```

**Extending Git Operations**
Add methods to `git_handler.py`:
```python
def compare_branches(self, branch_a: str, branch_b: str) -> str:
    # Branch comparison logic
    pass
```

**Diff Generation Methods**
The GitHandler provides two diff generation methods:
- `get_commit_diff()` - Returns raw git diff output (used for AI analysis to save tokens)
- `get_commit_diff_formatted()` - Returns formatted diff with ANSI colors (used for UI display)

Example usage:
```python
# For AI analysis (raw, compact)
raw_diff = git_handler.get_commit_diff()
analyzer.analyze_commit_changes(stats, raw_diff, architecture)

# For user display (formatted, colored)
formatted_diff = git_handler.get_commit_diff_formatted()
diff_screen = DiffScreen(formatted_diff)
```

**GitHub URL Generation**
The GitHandler provides commit URL generation for browser integration:
- `get_commit_url(commit_sha)` - Generates GitHub URL for a specific commit
- Handles multiple URL formats: https, git@, with/without .git extension
- Returns None for non-GitHub repositories

Example usage:
```python
# Get URL for current commit
url = git_handler.get_commit_url()  # Uses current commit

# Get URL for specific commit
url = git_handler.get_commit_url("a74c5da112c29466f182a03108337a488c785d76")
# Returns: https://github.com/owner/repo/tree/a74c5da112c29466f182a03108337a488c785d76
```

### Testing
```bash
# Syntax validation
python -m py_compile src/commit_teacher/**/*.py

# Run application (interactive mode)
python main.py

# Run with direct repository loading
python main.py --repo https://github.com/pallets/click

# Run without cache (fresh analysis)
python main.py --repo https://github.com/pallets/click --no-cache

# Test with small repo
# Try: https://github.com/pallets/click (good commit structure)
```

### Command-Line Interface

The application supports several command-line arguments:

```bash
python main.py [OPTIONS]

Options:
  --repo, -r URL        GitHub repository URL to analyze
  --local, -l PATH      Path to local Git repository
  --no-cache            Disable cache and perform fresh analysis
  --resume              Force resume from last viewed commit
  --version             Show version and exit
  --help                Show help message and exit
```

**Examples:**
```bash
# Interactive mode with setup screen
python main.py

# Load remote repository directly
python main.py --repo https://github.com/badlogic/pi-mono

# Load local repository
python main.py --local ~/projects/my-app
python main.py --local ./my-project

# Fresh analysis without cache
python main.py --repo https://github.com/pallets/click --no-cache
python main.py --local ./my-project --no-cache

# Force resume from last position
python main.py --repo https://github.com/badlogic/pi-mono --resume
```

**Behavior:**
- **Without --repo or --local**: Shows interactive setup screen (accepts both URLs and local paths)
- **With --repo**: Skips setup, clones remote repository directly
- **With --local**: Skips setup, loads local repository directly
- **Cache**: Enabled by default, use --no-cache to disable
- **Resume**: Automatic if cache exists, --resume forces it
- **Local Paths**: Supports ~/ (home directory), ./ (relative), and absolute paths

## Technical Decisions

### Why Chronological Order?
Commits are processed oldest to newest to mirror actual development. This helps learners understand organic evolution rather than just final state.

### Why Architecture Tracking?
Maintaining a living document helps learners see the big picture while diving into details. The AI updates it only when significant structural changes occur.

### Why Textual for TUI?
- Modern, reactive framework
- Rich styling and layout capabilities
- Built-in keyboard shortcuts and async support
- Better than curses/urwid for complex UIs

### Why Gemini API?
- Large context window for code analysis
- Strong code understanding capabilities
- Cost-effective for educational use
- Simple API (migrated from Anthropic Claude)

### Custom Diff Formatting
- Uses ANSI escape codes for colorized diff output
- Green for additions, red for deletions
- Cyan for file headers, blue for hunk markers
- Zero external dependencies (no dunk required)
- Better readability than plain git diff
- Used only for UI display (AI still gets raw diff for token efficiency)

## Performance Optimization

**Async Operations**
UI remains responsive during:
- Repository cloning (git operations)
- AI analysis (API calls)
- File reading (I/O operations)

**Caching Strategy**
- **Commit Analysis Caching**: AI-generated explanations stored in `<repo>.cache.json`
  - Prevents redundant API calls for previously analyzed commits
  - Cache checked before every AI analysis request
  - Cached results loaded instantly (no API latency)
  - Cache persists across application restarts
- **Session Resumption**: Automatically resumes from last viewed commit
  - Position saved after each commit navigation
  - On restart, navigates directly to last position
  - Loads all cached explanations along the way
- **Cache Management**:
  - New commits detected automatically (only analyze uncached commits)
  - Cache invalidation handled gracefully on repository changes
  - UI displays cache coverage and status in real-time
- **In-Memory Caching**:
  - Architecture document cached in memory during session
  - File tree generated once per commit
  - Commit list loaded at initialization

**Token Management**
- Limit initial file analysis to 20 files
- Skip large files (>10KB)
- Truncate diffs to reasonable size
- Focused prompts to minimize tokens

## API Integration

### Gemini API Usage
```python
import google.generativeai as genai

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-pro")

response = model.generate_content(prompt)
result = response.text
```

### Migration from Anthropic
Previous implementation used Claude API:
```python
# Old: Anthropic
from anthropic import Anthropic
client = Anthropic(api_key=key)
message = client.messages.create(...)
text = message.content[0].text

# New: Gemini (simpler)
import google.generativeai as genai
model = genai.GenerativeModel(model_name)
response = model.generate_content(prompt)
text = response.text
```

## User Interface

### Commit Screen Keybindings
- **n**: Navigate to next commit
- **p**: Navigate to previous commit
- **d**: Show git diff for current commit
- **c**: Open chat interface for questions
- **q**: Quit application

### GitHub Integration
- Commit SHAs are displayed in full (40 characters) and are clickable
- Clicking a SHA opens the commit in your default browser
- Format: `https://github.com/{owner}/{repo}/tree/{sha}`
- Works with any GitHub repository URL format (https, git@, with/without .git)

### Cache Status Display
The commit screen header shows real-time cache information:
```
Commit 5 of 42
SHA: abc1234 | 2025-11-12 14:30:00
Cache: 5/42 (12%) | [CACHED]
```

- **Cache coverage**: Shows how many commits are cached vs total
- **[CACHED]**: Current commit loaded from cache (instant, no API call)
- **[ANALYZED]**: Current commit freshly analyzed by AI (API call made)

## Error Handling

**Repository Cloning**
- Validates URL format
- Handles network failures gracefully
- Provides clear error messages in UI

**API Failures**
- Catches API errors and displays in UI
- Continues operation if possible
- No crashes on API timeouts

**File Operations**
- Handles missing files silently
- Skips unreadable files
- Validates paths before access

**Cache Operations**
- Handles corrupt cache files gracefully (creates new cache)
- Logs cache operations for debugging
- Saves cache incrementally (after each commit analysis)

## Future Enhancement Ideas

- Support for local repositories (not just GitHub)
- Multiple AI provider support (OpenAI, Claude, etc.)
- Export learning session to markdown
- Visual diff viewer
- Branch comparison mode
- Bookmark important commits
- Search across commit history
- Integration with code editors
- Collaborative learning sessions
- Cache Q&A responses per commit
- Manual cache invalidation command
- Export cache statistics and learning progress
