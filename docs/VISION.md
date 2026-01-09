# Glee Vision

## The Problem

Coding agents are everywhere — Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and more are shipping weekly. They're powerful. They're fast. But they all share the same fundamental problems:

1. **They work alone.** Each agent operates in isolation, with its own biases and blind spots. No peer review. No second opinion.

2. **They have no memory.** Every session starts fresh. They don't remember your project's conventions, past decisions, or lessons learned. You explain the same context over and over. Worse: some agents (Claude Code) use directory paths as project identifiers — rename a folder and all your history vanishes. Months of context, gone.

3. **They're interchangeable.** Today's best agent is tomorrow's second choice. But switching means losing all context and starting over.

## The Insight

The solution isn't to build another coding agent.

The solution is to build **an orchestration layer** that coordinates them all.

## What is Glee?

Glee is the **Stage Manager for Your AI Orchestra**.

Not a replacement. A multiplier.

```
Without Glee:
┌─────────────┐
│   Agent     │ → Works alone, no memory, no checks
└─────────────┘

With Glee:
┌─────────────────────────────────────────────────────────────┐
│                           Glee                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │MCP Server│  │A2A Server│  │ REST API │  │  Web UI    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────────┘   │
│       └─────────────┴─────────────┘                          │
│                     │                                        │
│       ┌─────────────┴─────────────┐                         │
│       │  Orchestrator + Memory    │                         │
│       └─────────────┬─────────────┘                         │
│                     │ subprocess                             │
└─────────────────────┼───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐     ┌───────────┐     ┌──────────┐
│ Primary │     │ Secondary │     │  Memory  │
│Reviewer │     │ Reviewer  │     │  Store   │
├─────────┤     ├───────────┤     ├──────────┤
│ Codex   │     │  Gemini   │     │ LanceDB  │
│ (default)│    │ (optional)│     │ DuckDB   │
└─────────┘     └───────────┘     └──────────┘
```

**Key Design Decisions**:
- **Main agent handles coding** - no separate "coder" role
- **Reviewers are preferences** - primary (default: codex) and secondary (optional)
- **User decides** - one reviewer at a time, user controls what feedback to apply
- **Maximum 2 reviewers** - keeps review focused, avoids analysis paralysis

**Protocol In, Subprocess Out**:
- Claude Code connects via MCP protocol (`glee mcp` server)
- `glee init` registers MCP server in project's `.mcp.json`
- Glee invokes CLI agents via subprocess
- Output logged to `.glee/stream_logs/` for observability

## Three Pillars

### 1. Intelligent Review Protocol

Agents make mistakes. Code gets shipped with bugs, security holes, and anti-patterns.

Glee provides structured, professional code review:

- Configurable reviewer preferences (primary + secondary)
- Severity levels (MUST/SHOULD, HIGH/MEDIUM/LOW)
- User-controlled feedback application
- Second opinion on demand

**Not "does this code look okay?" — but systematic quality assurance.**

### 2. Agent Abstraction Layer

Today you use Claude Code. Tomorrow maybe Codex is better for your use case. Next month, a new player emerges.

Glee abstracts the underlying agent:

- Unified interface across all coding agents
- Switch reviewers without losing context
- Best tool for each job

**Use any agent as your main coder. Configure any agent as your reviewer.**

### 3. Persistent Memory

This is the biggest gap in today's coding agents.

Glee remembers everything:

- **Project memory**: Architecture decisions, conventions, tech stack choices
- **Review memory**: Past issues, common mistakes, what worked
- **Learning**: Gets smarter about your codebase over time

**Storage (Embedded, No Server)**:

```
# Global config
~/.config/glee/
├── config.yml              # Global defaults
├── projects.yml            # Project registry (ID → path)
└── credentials.yml         # API keys

# Project config (gitignore .glee/)
<project>/.glee/
├── config.yml              # project.id, reviewers config
├── memory.lance/           # LanceDB - vector search
├── memory.duckdb           # DuckDB - SQL queries
├── stream_logs/            # Agent stdout/stderr logs
└── sessions/               # Session cache
```

**Tech stack**:
```
fastembed (local embedding, no API)
    ↓
LanceDB (vector storage + semantic search)
    ↓
DuckDB (SQL queries)
```

**Project ID is stable**: Renaming/moving projects doesn't lose history.

**Auto-injection via hooks**: When you start a new session, Glee automatically injects relevant context.

## The Flywheel

```
Better Reviews → Fewer Bugs → More Trust → More Usage
     ↓                                         ↓
More Memory → Smarter Context → Better Code ←──┘
```

This is the moat:
- **Review quality**: Structured feedback catches issues single agents miss
- **Memory compounds**: Every review, every decision makes Glee smarter
- **User control**: HITL ensures human oversight at every step

## Design Principles

### 1. Stage Manager, Not Conductor

Glee coordinates and logs. The main agent (Claude, etc.) does the creative work. Reviewers provide feedback. Humans make decisions.

### 2. Agent Agnostic

No lock-in to any single agent. Glee works with Claude Code, Codex, Gemini CLI, and whatever comes next.

### 3. Local First

Your code stays on your machine. Agents run locally with full capabilities. Memory is local.

### 4. Zero Config Start

`glee init` and you're running. Complexity is opt-in, not required.

### 5. Human In The Loop

User always decides what feedback to apply. No autonomous code changes without explicit approval.

## Current State

**Working features:**
- MCP integration with Claude Code
- Reviewer preference management (primary + secondary)
- Structured code review with severity levels
- Persistent memory (LanceDB + DuckDB)
- Stream logging for observability

**CLI commands:**
```bash
glee init                              # Initialize project
glee config set reviewer.primary codex # Set primary reviewer
glee config set reviewer.secondary gemini # Set secondary reviewer
glee status                            # View configuration
glee review src/                       # Run code review
```

## The Future

### V2: Advanced Memory
- Automatic context injection based on task
- Learn from every review and decision
- Cross-project knowledge sharing

### V3: Intelligent Dispatch
- Auto-detect task type for review focus
- Smart task decomposition for subagents

### V4: Team & Enterprise
- Shared memory across team
- GitHub/GitLab integration
- Audit logs and compliance

## Why "Glee"?

A glee club is a group of voices singing in harmony. No single voice dominates — each contributes its unique part to create something greater than any could alone.

That's what we're building: a harmonious collaboration between AI agents, each contributing their strengths, coordinated into better code.

---

_Glee: Stage Manager for Your AI Orchestra._
