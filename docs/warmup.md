# Session Continuity & Warmup

How Glee maintains context across coding sessions.

## Problem

Vibe coding breaks flow when a new session starts. Users re-explain context, re-open the same files, and re-justify decisions. Glee owns the "session continuity" wedge: resume a project in under 30 seconds with the right context.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Session Start                          Session End              │
│  ─────────────                          ───────────              │
│  SessionStart hook                      SessionEnd hook          │
│         │                                    │                   │
│         ▼                                    ▼                   │
│  ┌──────────────┐                    ┌───────────────┐          │
│  │ glee warmup- │                    │ glee          │          │
│  │ session      │                    │ summarize-    │          │
│  │ Reads:       │                    │ session       │          │
│  │ - goal       │                    │               │          │
│  │ - constraints│                    │ Writes:       │          │
│  │ - decisions  │                    │ - summary     │          │
│  │ - open_loops │                    │ - git_base    │          │
│  │ - changes    │                    │ - changes     │          │
│  │ - sessions   │                    │               │          │
│  └──────┬───────┘                    └───────┬───────┘          │
│         │                                    │                   │
│         ▼                                    ▼                   │
│  ┌──────────────────────────────────────────────────────────────┐
│  │                  .glee/memory.*                               │
│  │  (LanceDB vectors + DuckDB structured)                       │
│  └──────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

## Memory Categories

Glee uses reserved memory categories for session continuity:

| Category | Clear on Write? | Max Items | Purpose |
|----------|-----------------|-----------|---------|
| `goal` | Yes | 1 | Current objective |
| `constraint` | Yes | 5 | Key constraints to remember |
| `decision` | No (append) | 5 | Decisions made |
| `open_loop` | Yes | 5 | Unfinished tasks |
| `recent_change` | Yes | 20 | File changes since last session |
| `session_summary` | No (append) | 1 | Session end summary |

### Clear vs Append

- **Clear first** (`goal`, `constraint`, `open_loop`, `recent_change`): These represent "current state" — old values are replaced.
- **Append** (`decision`, `session_summary`): These are historical — we want to accumulate them.

## Git-Aware Change Tracking

Glee tracks what changed between sessions using git:

```
Session N ends:
  1. Get current HEAD → store as git_base in session_summary metadata
  2. Calculate changes since previous git_base → store as recent_change

Session N+1 starts (warmup):
  1. Read git_base from latest session_summary metadata
  2. Run: git diff --name-status {git_base}..HEAD
  3. Show "Changes Since Last Session"
```

This means warmup shows *actual* code changes since the last session, not just uncommitted changes.

## Data Flow

### Session Summarization (LLM-based)

When a session ends, `glee summarize-session --from=claude` is called by the SessionEnd hook. It:

1. Reads the Claude Code session transcript
2. Calls the specified agent (Claude) to generate structured output:
   ```json
   {
     "goal": "The main task or objective",
     "decisions": ["Decision 1", "Decision 2"],
     "open_loops": ["Unfinished task 1"],
     "summary": "2-3 sentence summary"
   }
   ```
3. Saves the structured data to memory via `capture_memory()`

All activity is logged to `.glee/stream_logs/summarize-session-YYYYMMDD.log` for debugging.

### Warmup (`build_warmup_text`)

Called by:
- `glee warmup-session` CLI command
- `SessionStart` hook (auto-injected)

Output format:

```markdown
# Glee Warmup

## Last Session
- task-abc123 (completed, 2025-01-10 14:30): Implement warmup module

## Current Goal
Implement session continuity for vibe coding

## Key Constraints
- No cloud dependencies
- Must be fast (<30s warmup)

## Recent Decisions
- Use LanceDB for vectors
- Store git_base in metadata

## Changes Since Last Session
- M glee/warmup.py
- A glee/helpers.py
- M glee/mcp_server.py

## Open Loops
- Hook registration not implemented
- Need to add TTL for decisions

## Memory
### Architecture
- CLI built with Typer, MCP server with mcp.server
### Convention
- Use snake_case for Python, type hints required
```

## Hook Integration

### Claude Code

When you run `glee init claude`, Glee registers hooks in `.claude/settings.local.json`:

```json
// .claude/settings.local.json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{ "type": "command", "command": "glee warmup-session 2>/dev/null || true" }]
    }],
    "SessionEnd": [{
      "matcher": "",
      "hooks": [{ "type": "command", "command": "glee summarize-session --from=claude 2>/dev/null || true" }]
    }]
  }
}
```

### Other Agents

See [coding-agent-hooks.md](./coding-agent-hooks.md) for hook configuration for Cursor, Gemini CLI, Codex, etc.

## MCP Tools

| Tool | Purpose |
|------|---------|
| `glee_memory_add` | Add a memory entry to a category |
| `glee_memory_list` | List memories, optionally filtered by category |
| `glee_memory_delete` | Delete memory by ID or category |

Note: Warmup and session summarization are handled automatically by hooks (`SessionStart` and `SessionEnd`), not via MCP tools.

## CLI Commands

```bash
# Output warmup context to stdout
glee warmup-session

# Summarize session (automatically called by SessionEnd hook)
# Hook mode: reads session data from stdin, saves to DB
glee summarize-session --from=claude

# Manual mode: prints structured summary, no save
glee summarize-session --from=claude --session-id=abc123

# Add memory manually
glee memory add --category goal --content "Build auth"
glee memory add --category constraint --content "Use JWT"
```

## Success Metrics

- Time-to-first-action <30s after session start
- Fewer repeated explanations (qualitative)
- Users can resume mid-task without re-explaining context
