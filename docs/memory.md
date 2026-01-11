# Glee Memory System

Glee Memory provides persistent project knowledge that survives across sessions. It combines vector search for semantic similarity with structured storage for fast lookups.

## Storage Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Vector | LanceDB | Semantic similarity search |
| Structured | DuckDB | SQL queries, category filtering |
| Embeddings | fastembed (BAAI/bge-small-en-v1.5) | Local embedding generation |

All data is stored in `.glee/`:
- `memory.lance/` - Vector embeddings
- `memory.duckdb` - Structured data

## Categories

Memories are organized by category. Standard categories:

| Category | Use For |
|----------|---------|
| `architecture` | System design, module structure, data flow |
| `convention` | Coding standards, naming patterns, file organization |
| `review` | Common review feedback, recurring issues |
| `decision` | Technical decisions and rationale |
| `goal` | Current project goal or target outcome |
| `constraint` | Key constraints to keep in mind |
| `open_loop` | Unfinished tasks or blockers |
| `recent_change` | Notable changes since last session |
| `session_summary` | Short session summaries |

**Custom categories are supported.** Use any string as a category name (e.g., `security`, `api-design`, `testing`).

## CLI Commands

```bash
# Add a memory
glee memory add --category architecture --content "API uses REST with versioned endpoints /v1/*"
glee memory add --category convention --content "Use snake_case for Python, camelCase for TypeScript"
glee memory add --category my-custom-category --content "Custom category content"
glee memory add --category decision --content "Use FastAPI" --metadata '{"source":"adr-001","owner":"api"}'

# List memories
glee memory list                    # All memories
glee memory list --category architecture  # Filter by category

# Search (semantic similarity)
glee memory search "how do we handle authentication"
glee memory search "error handling" --category convention

# Get formatted overview (for context injection)
glee warmup-session          # Session warmup (goal, constraints, decisions, open loops, changes, memory)
glee memory overview # Memory-only overview

# Structured capture
glee memory add --category goal --content "Ship v1"
glee memory add --category decision --content "Use FastAPI"

# Delete
glee memory delete --by id --value abc123              # Delete by ID
glee memory delete --by category --value review --confirm # Delete all in category

# Statistics
glee memory stats
```

Top-level shortcut:
```bash
glee warmup-session  # Session warmup context (goal, constraints, decisions, open loops, changes, memory)
```

## MCP Tools

When Claude Code runs in a Glee project, these tools are available:

| Tool | Description |
|------|-------------|
| `glee_memory_add` | Add a memory entry to a category |
| `glee_memory_list` | List memories, optionally filtered by category |
| `glee_memory_delete` | Delete memory by ID or category |
| `glee_memory_search` | Semantic search across memories |
| `glee_memory_overview` | Get formatted overview for context |
| `glee_memory_stats` | Get memory statistics |
| `glee_memory_bootstrap` | Bootstrap memory from docs + structure |

Note: Warmup and session summarization are handled automatically by hooks. Structured session capture (goal, decisions, open_loops, summary) is handled automatically by the `SessionEnd` hook via `glee summarize-session --from=claude`.

Example MCP calls:
```text
glee_memory_add(category="decision", content="Use FastAPI")
glee_memory_search(query="auth flow", limit=5)
glee_memory_delete(by="id", value="abc123")
glee_memory_delete(by="category", value="review", confirm=true)
```

### Memory Bootstrap

`glee_memory_bootstrap` is special - it doesn't require an external LLM API. It gathers:

1. **Documentation**: README.md, CLAUDE.md, CONTRIBUTING.md, docs/
2. **Package config**: pyproject.toml, package.json, Cargo.toml, go.mod
3. **Directory structure**: Top 2 levels, excluding noise

Then returns this context with instructions. Claude Code (already an LLM) analyzes it and calls `glee_memory_add` to populate memories for architecture, conventions, dependencies, and decisions.

## Auto-Injection

When you run `glee init claude`, Glee registers hooks in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "glee warmup-session 2>/dev/null || true"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "glee summarize-session --from=claude 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

This:
- **SessionStart**: Injects warmup context (goal, constraints, decisions, open loops, changes, memory)
- **SessionEnd**: Uses the agent (Claude) to generate a structured summary (goal, decisions, open_loops, summary) and stores it in memory. Logs to `.glee/stream_logs/` for debugging.

## Usage Patterns

### Building Project Memory

As you work, add important context:

```bash
# After making architectural decisions
glee memory add --category decision --content "Chose PostgreSQL over MongoDB for ACID compliance"

# When establishing patterns
glee memory add --category convention --content "All API errors return {error: string, code: number}"

# After reviews reveal patterns
glee memory add --category review --content "Always check null before accessing nested properties"
```

### Semantic Search

Find relevant memories even with different wording:

```bash
# Finds memories about authentication, auth, login, etc.
glee memory search "user login flow"

# Finds memories about error handling patterns
glee memory search "what to do when API fails"
```

### Managing Memory Conflicts

If old information conflicts with new:

1. Delete the outdated memory: `glee memory delete --by id --value <id>`
2. Add the updated information: `glee memory add --category <category> --content "<new content>"`

There's no `update` command - vectors must be regenerated when content changes, so delete + add is the correct workflow.

## Data Model

Each memory entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | 8-character UUID |
| `category` | string | Category name |
| `content` | string | The memory content |
| `metadata` | JSON | Optional metadata |
| `created_at` | datetime | Creation timestamp |
| `vector` | float[] | 384-dim embedding (LanceDB only) |

## Limitations

- **Personal only**: Memories are stored locally in `.glee/`, not shared across team
- **No versioning**: Old content is deleted, not archived
- **No conflict resolution**: Users manage conflicts manually

## Files

```
.glee/
├── memory.lance/     # Vector database
├── memory.duckdb     # Structured database
└── config.yml        # Project config
```
