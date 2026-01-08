# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Glee is a Multi-Agent Code Collaboration Platform - an MCP (Model Context Protocol) server that enables Claude Code to get code reviews from other AI CLI tools (Codex, Gemini, etc.). The review loop continues until approved or max iterations (10) reached.

## Commands

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode - default)
uv run python -m glee

# Run MCP server (SSE mode for Docker)
GLEE_TRANSPORT=sse uv run python -m glee

# Database migrations
uv run alembic upgrade head
uv run alembic revision -m "description"

# Docker
docker compose up -d
docker exec -it glee-server codex login --device-auth
```

## Architecture

```
Claude Code (host)
    ↓ MCP Protocol
Glee MCP Server (glee/server.py)
    ↓ calls
LangGraph Workflow (glee/graph/review_graph.py)
    ↓ invokes
Codex CLI wrapper (glee/services/codex_cli.py)
    ↓ subprocess
codex exec --json --full-auto
```

**Key design decisions:**
- Agent only calls Codex for review - code modifications stay in Claude Code session
- MCP Server exposes 3 tools: `start_review`, `continue_review`, `get_review_status`
- Supports stdio (local) and SSE (Docker) transports via `GLEE_TRANSPORT` env var
- Session state stored in `.glee/sessions/` (JSON) or MySQL (Docker)

## Module Structure

- `glee/server.py` - MCP server with tool handlers, transport selection
- `glee/types.py` - Pydantic models (ReviewSession, ReviewStatus, CodexOutput)
- `glee/graph/review_graph.py` - LangGraph state machine for review loop
- `glee/services/codex_cli.py` - Codex CLI subprocess wrapper, JSONL parsing
- `glee/state/` - Session management and storage abstraction
- `glee/db/migrations/` - Alembic database migrations

## Environment Variables

- `GLEE_TRANSPORT` - `stdio` (default) or `sse`
- `GLEE_HOST` / `GLEE_PORT` - SSE server binding (default: 127.0.0.1:8080)
- `DATABASE_URL` - MySQL connection for Docker mode
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` - AI CLI authentication
