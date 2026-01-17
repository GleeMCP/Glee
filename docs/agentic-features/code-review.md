# Code Review

> Local and remote code review with AI reviewers.

## Overview

| Mode | Target | Status | Output |
|------|--------|--------|--------|
| **Local** | Files, directories, git changes | ✅ Working | Terminal/MCP response |
| **Remote PR** | `github:pr#123` | ✅ Working | Markdown report (comments pending) |
| **Remote Branch** | `github:branch/feature` | ⏳ Pending | Markdown report |

---

## Current Implementation

### Architecture

```
glee code-review <target>
    ↓
Agent Adapter (Claude/Codex/Gemini CLI)
    ↓
Review Result (stdout)
```

### Supported Targets

| Target | Description |
|--------|-------------|
| `file.py` | Single file |
| `src/` | Directory |
| `git:changes` | Uncommitted changes (`git diff`) |
| `git:staged` | Staged changes (`git diff --staged`) |
| `"description"` | Freeform description |

### CLI Usage

```bash
# Basic review
glee code-review src/

# Review uncommitted changes
glee code-review git:changes

# Focus on specific areas
glee code-review . --focus "security,performance"

# Get second opinion from another reviewer
glee code-review . --second-opinion
```

### MCP Tool

```
glee.code_review(target, focus?, log_level?)
```

Runs in thread pool (non-blocking for MCP event loop), streams output via MCP log notifications.

### Agent Adapters

| Adapter | CLI | Status |
|---------|-----|--------|
| `claude` | `claude -p "..." --output-format text` | ✅ Working |
| `codex` | `codex exec --json --full-auto "..."` | ✅ Working |
| `gemini` | `gemini -p "..."` | ✅ Working |

### Configuration

```yaml
# .glee/config.yml
reviewers:
  primary: codex    # Required
  secondary: claude # Optional (for --second-opinion)
```

---

## Planned: Local vs Remote Review

### Design Principles

1. **Local = Blocking**: Reviewer reads files while you wait. Don't edit code during review.
2. **Remote = Async**: Fetches from GitHub, reviews in background, delivers results.
3. **PR Comments**: When reviewing a PR, post inline comments directly to GitHub.

### Target Syntax

```
# Local (blocking)
glee code-review <path>           # File or directory
glee code-review git:changes      # Uncommitted
glee code-review git:staged       # Staged

# Remote (async)
glee code-review github:pr#123              # PR in current repo
glee code-review github:owner/repo#123      # PR in another repo
glee code-review github:branch/feature      # Branch vs main
glee code-review github:main...feature      # Explicit base..head
```

### Execution Model

```
┌─────────────────────────────────────────────────────────────┐
│                      glee code-review                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Local Target?                 Remote Target?               │
│  ┌─────────────┐              ┌─────────────┐               │
│  │  BLOCKING   │              │    ASYNC    │               │
│  │             │              │             │               │
│  │ Read files  │              │ Fetch diff  │               │
│  │ Run review  │              │ via GitHub  │               │
│  │ Print result│              │ API         │               │
│  │             │              │             │               │
│  │ Wait...     │              │ Background  │               │
│  │             │              │ review      │               │
│  │ Done!       │              │             │               │
│  └─────────────┘              │ Deliver:    │               │
│                               │ - PR: inline│               │
│                               │   comments  │               │
│                               │ - Branch:   │               │
│                               │   .md report│               │
│                               └─────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## Remote Review: GitHub Integration

### Authentication

Reuse `glee connect` with a new "Services" category:

```
glee connect

  ─── AI Providers ───
    1  Codex        · OpenAI OAuth
    2  Copilot      · GitHub OAuth
    3  OpenAI SDK   · OpenRouter, Groq, etc.
    4  Anthropic    · Direct API
    5  Vertex AI    · Google Cloud
    6  Bedrock      · AWS

  ─── Services ───
    7  GitHub       · PR reviews, API access

Select: 7

  GitHub Personal Access Token
  Create at: https://github.com/settings/tokens
  Scopes needed: repo, read:org

  Token: ghp_xxx
  ✓ GitHub connected
```

Stored in `~/.config/glee/connections.yml`:

```yaml
- id: xyz789
  label: github
  category: service
  type: api
  vendor: github
  key: "ghp_xxx"
```

### PR Review Flow

```
glee code-review github:pr#123
    │
    ├─ 1. Fetch PR metadata
    │     GET /repos/{owner}/{repo}/pulls/{number}
    │
    ├─ 2. Fetch PR diff
    │     GET /repos/{owner}/{repo}/pulls/{number}/files
    │
    ├─ 3. Run AI review (async)
    │     - Parse diff hunks
    │     - Identify issues with file:line references
    │
    ├─ 4. Post inline comments to GitHub (multiple, like human review)
    │     POST /repos/{owner}/{repo}/pulls/{number}/comments
    │     {
    │       "path": "src/foo.py",
    │       "line": 42,
    │       "body": "[HIGH] SQL injection risk..."
    │     }
    │
    ├─ 5. Write report to file
    │     .glee/reviews/pr-123-{timestamp}.md
    │
    └─ 6. Notify user
```

### Branch Review Flow

```
glee code-review github:branch/feature
    │
    ├─ 1. Determine base branch (main/master)
    │
    ├─ 2. Fetch comparison
    │     GET /repos/{owner}/{repo}/compare/{base}...{head}
    │
    ├─ 3. Run AI review (async)
    │
    ├─ 4. Write report to file
    │     .glee/reviews/{branch}-{timestamp}.md
    │
    └─ 5. Notify user
```

### Notifications

When async review completes, notify via osascript (macOS) / notify-send (Linux):

```python
import subprocess
import platform

def notify(title: str, message: str) -> None:
    """Send desktop notification."""
    if platform.system() == "Darwin":
        script = f'display notification "{message}" with title "{title}" sound name "Funk"'
        subprocess.run(["osascript", "-e", script])
    elif platform.system() == "Linux":
        subprocess.run(["notify-send", title, message])

# Example:
# notify("✨ Glee", "✅ PR #123 Reviewed\n📋 3 issues found")
```

### Review Output Format

PR inline comments use severity tags:

```
[HIGH] Security: SQL injection vulnerability
[MEDIUM] Performance: N+1 query in loop
[LOW] Style: Prefer `const` over `let`
[SHOULD] Consider adding error handling
[MUST] Fix memory leak before merge
```

---

## Implementation Plan

### Phase 1: GitHub Client Module

Create `glee/github/` module:

```
glee/github/
├── __init__.py
├── client.py      # GitHub API wrapper
├── auth.py        # Token management
├── pr.py          # PR operations
└── diff.py        # Diff parsing utilities
```

**Key Functions:**

```python
# client.py
class GitHubClient:
    def __init__(self, token: str | None = None): ...
    async def get_pr(self, owner: str, repo: str, number: int) -> PR: ...
    async def get_pr_files(self, owner: str, repo: str, number: int) -> list[PRFile]: ...
    async def post_review(self, owner: str, repo: str, number: int, review: Review) -> None: ...
    async def compare(self, owner: str, repo: str, base: str, head: str) -> Comparison: ...
```

### Phase 2: Remote Review Module

Create `glee/review/` module:

```
glee/review/
├── __init__.py
├── local.py       # Extract current local review logic
├── remote.py      # New remote review logic
├── targets.py     # Target parsing (github:pr#123, etc.)
└── report.py      # Report generation
```

**Target Parsing:**

```python
# targets.py
from dataclasses import dataclass
from enum import Enum

class TargetType(Enum):
    LOCAL_PATH = "local_path"
    GIT_CHANGES = "git_changes"
    GIT_STAGED = "git_staged"
    GITHUB_PR = "github_pr"
    GITHUB_BRANCH = "github_branch"

@dataclass
class ReviewTarget:
    type: TargetType
    value: str
    owner: str | None = None  # For GitHub targets
    repo: str | None = None
    number: int | None = None  # PR number
    base: str | None = None   # For branch comparison
    head: str | None = None

def parse_target(target: str) -> ReviewTarget:
    """Parse review target string into structured target."""
    if target.startswith("github:pr#"):
        # github:pr#123 or github:owner/repo#123
        ...
    elif target.startswith("github:branch/"):
        # github:branch/feature
        ...
    elif target.startswith("git:"):
        # git:changes or git:staged
        ...
    else:
        # Local path
        ...
```

### Phase 3: CLI & MCP Updates

**CLI Changes:**

```bash
# New flags
glee code-review github:pr#123 --dry-run      # Show what would be posted
glee code-review github:pr#123 --no-post      # Review but don't post comments
glee code-review github:branch/feature --output report.md

# Async status
glee code-review --status                     # Show running/completed reviews
glee code-review --status <review-id>         # Show specific review
```

**MCP Updates:**

```python
# New MCP tool parameters
glee.code_review(
    target="github:pr#123",
    focus=["security"],
    dry_run=False,        # If true, don't post to GitHub
    post_comments=True,   # If false, return report only
)
```

### Phase 4: Async Job Tracking

For remote reviews, track job status:

```
.glee/reviews/
├── jobs.json              # Active/completed jobs
├── pr-123-2024-01-15.md   # Review reports
└── feature-2024-01-15.md
```

**Job Schema:**

```python
@dataclass
class ReviewJob:
    id: str
    target: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None
    result_path: str | None  # Path to report file
    github_review_id: int | None  # If posted to GitHub
    error: str | None
```

---

## Implementation Status

### ✅ Done

#### Phase 1: GitHub Client Module
- [x] `glee/github/__init__.py` - Module exports
- [x] `glee/github/auth.py` - Token from `glee connect` (connections.yml)
- [x] `glee/github/client.py` - Async httpx client with PR/files/compare methods
- [x] `glee/github/diff.py` - Diff parsing utilities

#### Phase 1.5: glee connect Update
- [x] New TUI with divider-style categories
- [x] "Services" category with GitHub option (#7)
- [x] Token stored in `~/.config/glee/connections.yml`

#### Phase 2: CLI & MCP (Partial)
- [x] `glee code-review github:pr#123` - Fetches PR, runs AI review
- [x] `--dry-run` flag - Preview without posting
- [x] Report saved to `.glee/reviews/pr-{n}-{timestamp}.md`
- [x] Desktop notifications (osascript/notify-send, Funk sound)

#### Phase 3: Open Loop Integration
- [x] Completed reviews added to `open_loop` memory
- [x] Warmup session injects open loops
- [x] `glee.code_review.status` - List pending reviews
- [x] `glee.code_review.get(review_id)` - Read full report
- [x] `glee.memory.delete` - Acknowledge and close

### ⏳ Pending

#### Phase 2: Remote Review (Remaining)
- [ ] `github:branch/feature` target - Branch comparison review
- [ ] `github:owner/repo#123` - Cross-repo PR support
- [ ] Post inline comments to GitHub via API
- [ ] `--no-post` flag - Review without posting
- [ ] `--output` flag - Custom report path

#### Phase 4: Async & Job Tracking
- [ ] True async background reviews (currently blocking)
- [ ] Job storage in `.glee/reviews/jobs.json`
- [ ] `glee code-review --status` CLI command
- [ ] Job cleanup/retention policy

#### Tests
- [ ] Unit tests for GitHub client
- [ ] Integration tests for PR review flow

---

## Open Loop Integration

Completed reviews are tracked in glee's memory system for session continuity.

### Flow

```
1. PR review completes
   └─ Add to open_loop memory:
      "PR #123 review completed - 3 issues found"
      metadata: {type: review, review_id: pr-123-xxx, result_path: ...}

2. Next Claude Code session starts
   └─ glee warmup-session
      └─ Reads open_loop → injects:
         "## Open Loops
          - PR #123 review completed - 3 issues found"

3. Claude reads the review
   └─ glee.code_review.get("pr-123-xxx")
      └─ Returns full markdown report

4. Claude acknowledges
   └─ glee.memory.delete(by="id", value=memory_id)
      └─ Removes from open_loop
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `glee.code_review.status` | List pending/completed reviews |
| `glee.code_review.get(review_id)` | Get full review report |
| `glee.memory.delete(by="id", value=memory_id)` | Acknowledge and close item |

---

## Open Questions

1. **Comment threading**: Should follow-up reviews update existing comments or create new ones?

2. **Review state**: Should AI reviews ever use `REQUEST_CHANGES` (blocks merge) or always `COMMENT`?

3. **Rate limits**: How to handle GitHub API rate limits for large PRs with many files?

4. **Incremental review**: Should we support reviewing only new commits since last review?

---

## Future: Native Agent Runtime

> Long-term vision: Replace CLI subprocess with Glee-native agent loop.

### Current Problem

```
glee code-review src/
    ↓ subprocess
codex CLI (handles everything: file reading, reasoning, output)
    ↓
Review result
```

Glee is just a wrapper. We delegate all agentic capabilities to external CLIs.

### Target Architecture

```
glee code-review src/
    ↓
Glee Agent Runtime
    ├── LLM: Codex/Claude/Gemini API (direct)
    ├── Tools: core.file.*, core.git.*, core.shell.*
    └── Loop: ReAct (Reason → Act → Observe)
    ↓
Review result
```

Glee becomes a true agent. We control the tools, the loop, the prompts.

### Native Tools Module

```
glee/core/
├── file.py      # read, write, list, search, stat
├── git.py       # status, diff, log, show
└── shell.py     # Sandboxed execution (allowlist only)
```

**Security:**
- Path sandboxing: All file ops restricted to project root
- Command allowlist: Only safe commands (`npm test`, `pytest`, `ruff`, etc.)
- Timeout limits on all operations

### Agent Loop (ReAct)

```python
for iteration in range(MAX_ITERATIONS):
    # REASON: Ask LLM what to do
    response = await llm.chat(messages, tools=tool_schemas)

    if response.finish_reason == "stop":
        return response.content  # Done

    # ACT: Execute tool calls
    for tool_call in response.tool_calls:
        result = execute(tool_call.name, **tool_call.args)

        # OBSERVE: Add result to context
        messages.append(tool_result(tool_call.id, result))
```

### Benefits

| Aspect | CLI Subprocess | Native Agent |
|--------|----------------|--------------|
| Control | None (black box) | Full (tools, prompts, loop) |
| Streaming | Limited | Native |
| Tool visibility | Hidden | Logged & auditable |
| Cost control | None | Token budgets |
| Customization | Flags only | Full prompt engineering |

### Implementation Priority

This is a **Phase 5+** enhancement. Focus first on:
1. Local/remote review (Phases 1-4)
2. GitHub integration
3. Async job tracking

Then consider native agent runtime as an optimization.

---

## Related Docs

- [Subagents](../subagents.md) - Background task delegation
- [Observability](../observability.md) - Logging and monitoring
