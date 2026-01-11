# Glee Session Continuity & Warmup (Spec)

## Why This Exists

Vibe coding breaks flow when a new session starts. Users re-explain context, re-open the same files, and re-justify decisions. Glee should own the "session continuity" wedge: resume a project in under 30 seconds with the right context and next steps.

## Goals

- Make new sessions productive in <30s.
- Eliminate repeated context re-explanations.
- Keep it local-first, fast, and MCP-friendly.
- Require minimal manual input.

## Non-Goals

- Replace full code review workflows.
- Build a cloud service or external index.
- Maintain infinite context (focus on recency + relevance).

## Core Concepts

- **Project Brief**: A concise "what we are building" statement.
- **Decisions**: Durable choices and rationale (frameworks, architecture, constraints).
- **Preferences**: Conventions, style, and "do/don't" rules.
- **Open Loops**: Unfinished tasks, blockers, or TODOs.
- **Recent Changes**: What changed since last session (git-aware).

## Primary Flow (User)

1. Start a new session.
2. `glee warmup-session` runs automatically via `SessionStart` hook.
3. Get a short, structured summary injected into context.
4. Ask for deeper context only if needed (use memory search).

## CLI + Hook Surface

### 1) `glee warmup-session` (CLI)

Fast, single-shot continuity summary. Called automatically by `SessionStart` hook.

**Output (structured text, injected into context)**

- Current goal
- Key constraints
- Recent decisions
- Open loops
- Changes since last session
- Memory overview

### 2) `glee_memory_search` (MCP)

On-demand semantic search across memories.

**Inputs**

- `query` (required): search query
- `limit` (optional, default 10)
- `category` (optional): filter by category

**Output**

- Relevant memory entries ranked by similarity

### 3) `glee_spotcheck` (new name for fast review)

A quick confidence check. Top 3 high-risk issues only. Targeted for vibe coding.

**Inputs**

- `target` (optional): default `git:changes`
- `limit` (optional, default 3)

**Output**

- Top risks with severity and 1-line rationale
- Optional "ignore if intentional" notes

## Data Sources (MVP, local only)

- `.glee/memory.*` (existing memory store)
- `.glee/sessions/*.json` (existing task sessions)
- `git status` / `git diff --name-only`
- `README.md`, `CLAUDE.md`, `AGENTS.md`

## Data Model (Additive)

Use the existing memory store with richer categories + metadata.

**New categories**

- `brief` (1 entry)
- `decision`
- `preference`
- `open_loop`
- `recent_change`
- `session_summary`

**Metadata examples**

```json
{
  "source": "session",
  "session_id": "task-1a2b3c4d",
  "files": ["src/api/auth.py", "src/db/models.py"],
  "timestamp": "2025-01-10T12:34:56Z"
}
```

## Heuristics (Keep It Fast)

- Prefer recency: last session + git changes.
- Prefer relevance: memory search on `focus` if provided.
- Cap output size aggressively (hard limit).
- Avoid LLM summarization unless user asks.

## Hooks (Implemented)

- `SessionStart`: auto-run `glee warmup-session` → inject context
- `SessionEnd`: auto-run `glee summarize-session --from=<agent>` → LLM generates structured summary (goal, decisions, open_loops) → saves to memory

## Implementation Status

**Implemented:**

- `glee warmup-session` CLI command (called by SessionStart hook)
- `glee summarize-session --from=<agent>` CLI command (called by SessionEnd hook)
- LLM-based structured session summarization
- `glee_memory_*` MCP tools for memory management
- Semantic search via LanceDB

**Future:**

- Relevance ranking using semantic search + git diff weighting
- Background indexing and cache

## Success Metrics

- Time-to-first-action <30s after session start.
- Fewer repeated explanations (qualitative).
- Higher retention for users doing >3 sessions/week.

## Open Questions

- Do we want "resume" to be opinionated (suggest next steps), or purely factual?
- Where should open loops be captured (manual vs inferred)?

## What’s harder to copy (and where Glee wins):

- A persistent, agent‑agnostic memory store with stable project IDs (survives renames, works across Claude/Codex/Gemini).
- Automatic session summaries and open‑loop tracking written after tasks complete (not at session start).
- Diff‑aware context: “what changed since last session,” “what broke last time,” “what’s still unresolved.”
- A context pack that’s relevant to the current focus, not just a dump.
