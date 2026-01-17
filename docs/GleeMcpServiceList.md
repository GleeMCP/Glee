# Glee MCP Service List

> Comprehensive catalog of all MCP tools — existing and planned.

## Legend

| Status | Meaning |
|--------|---------|
| ✅ | Implemented and working |
| 🚧 | In progress |
| 📋 | Planned |

---

## Memory — `glee.memory.*`

Persistent project memory that survives across sessions.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.memory.add` | ✅ | Store insights, decisions, context |
| `glee.memory.search` | ✅ | Semantic search across memory |
| `glee.memory.overview` | ✅ | Get project summary |
| `glee.memory.list` | ✅ | List all memories |
| `glee.memory.delete` | ✅ | Delete a memory entry |
| `glee.memory.stats` | ✅ | Memory statistics |

---

## Code Review — `glee.code_review`

Get a second opinion from another AI.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.code_review` | ✅ | Review code with configurable AI reviewer |

---

## Configuration — `glee.config.*`

Project configuration management.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.config.set` | ✅ | Set configuration value |
| `glee.config.unset` | ✅ | Remove configuration value |
| `glee.status` | ✅ | Show project status and config |

---

## Git Forensics — `glee.git.*`

Deep git history analysis and insights.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.git.blame` | 📋 | Enhanced blame with context |
| `glee.git.history` | 📋 | File history with semantic analysis |
| `glee.git.hotspots` | 📋 | Find frequently changed files |
| `glee.git.contributors` | 📋 | Contributor analysis per file/directory |
| `glee.git.changes` | 📋 | Summarize recent changes |
| `glee.git.bisect` | 📋 | AI-assisted git bisect |

---

## Database Inspection — `glee.db.*`

Inspect and understand database schemas.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.db.connect` | 📋 | Connect to a database |
| `glee.db.schema` | 📋 | Get database schema |
| `glee.db.tables` | 📋 | List tables with row counts |
| `glee.db.describe` | 📋 | Describe table structure |
| `glee.db.sample` | 📋 | Sample rows from a table |
| `glee.db.query` | 📋 | Run read-only SQL query |
| `glee.db.explain` | 📋 | Explain query execution plan |

---

## Task Delegation — `glee.task`

Delegate tasks to background agents.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.task` | ✅ | Spawn an agent to execute a task (sync) |

### Planned Extensions — `glee.task.*`

| Tool | Status | Description |
|------|--------|-------------|
| `glee.task.submit` | 📋 | Submit async task, returns task_id |
| `glee.task.get` | 📋 | Get task status and progress |
| `glee.task.wait` | 📋 | Block until task completes |
| `glee.task.list` | 📋 | List all tasks |
| `glee.task.cancel` | 📋 | Cancel a running task |

---

## GitHub — `glee.github.*`

GitHub integration for PRs, issues, and more.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.github.pr.list` | 📋 | List pull requests |
| `glee.github.pr.get` | 📋 | Get PR details |
| `glee.github.pr.review` | 📋 | AI-powered PR review |
| `glee.github.pr.create` | 📋 | Create a pull request |
| `glee.github.issue.list` | 📋 | List issues |
| `glee.github.issue.get` | 📋 | Get issue details |
| `glee.github.issue.create` | 📋 | Create an issue |
| `glee.github.actions.status` | 📋 | Get CI/CD status |
| `glee.github.actions.logs` | 📋 | Get workflow run logs |

---

## RAG / Knowledge Base — `glee.rag.*`

Cross-project knowledge and documentation.

| Tool | Status | Description |
|------|--------|-------------|
| `glee.rag.index` | 📋 | Index documentation/codebase |
| `glee.rag.search` | 📋 | Search across indexed content |
| `glee.rag.ask` | 📋 | Ask questions about codebase |
| `glee.rag.sources` | 📋 | List indexed sources |

---

## Session Hooks (Non-MCP)

Automatic context management — not MCP tools, but integrated features.

| Feature | Status | Description |
|---------|--------|-------------|
| Session warmup | ✅ | Inject relevant context at session start |
| Session summarize | ✅ | Summarize and save to memory at session end |

---

## Summary

| Namespace | Implemented | Planned | Total |
|-----------|-------------|---------|-------|
| `glee.memory.*` | 6 | 0 | 6 |
| `glee.code_review` | 1 | 0 | 1 |
| `glee.config.*` | 2 | 0 | 2 |
| `glee.status` | 1 | 0 | 1 |
| `glee.task` | 1 | 5 | 6 |
| `glee.git.*` | 0 | 6 | 6 |
| `glee.db.*` | 0 | 7 | 7 |
| `glee.github.*` | 0 | 9 | 9 |
| `glee.rag.*` | 0 | 4 | 4 |
| **Total** | **11** | **31** | **42** |

---

*Want a tool that's not listed? [Open an issue](https://github.com/GleeMCP/Glee/issues). We ship fast.*
