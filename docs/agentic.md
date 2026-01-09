# How CLI Agents Work

This document explains how Glee orchestrates CLI-based AI agents and how those agents perform autonomous "agentic" tasks.

## The Key Insight

**CLI agents like Codex, Claude Code, and Gemini CLI are themselves full-featured agents with built-in tools.** They're not "dumb" CLIs that just return text.

When Glee invokes an agent via subprocess, that agent runs autonomously within its own process, using its own tools (file reading, web search, code execution, etc.).

## Architecture

```
Glee (stage manager)
    ↓ subprocess call: `codex exec --json --full-auto "prompt"`

Codex CLI (runs as its own process)
    ├── Receives prompt
    ├── Autonomously decides what to do
    ├── Uses ITS OWN built-in tools:
    │   ├── File reading
    │   ├── Code search/grep
    │   ├── Web search
    │   ├── Code execution
    │   └── etc.
    ├── Thinks, acts, observes, repeats
    └── Returns final response

Glee
    ↓ collects output
    ↓ logs to .glee/stream_logs/
```

## Analogy

Think of it like hiring a contractor:

- **Glee** = Stage manager who coordinates and logs everything
- **Main Agent** (Claude Code) = Principal performer who does the coding
- **Reviewer** (Codex/Gemini) = Quality inspector with their own expertise

The stage manager says "review this code" - they don't hand the inspector individual tools. The inspector shows up with their own equipment and expertise, does the job autonomously, and reports back.

## What Glee Actually Does

Glee doesn't give agents their capabilities. It:

1. **Manages reviewer preferences** (primary and secondary reviewer)
2. **Injects context** (shared memory, project info)
3. **Logs everything** to `.glee/stream_logs/` for observability
4. **Aggregates results** from reviews

The "agentic stuff" happens entirely within each CLI agent's process. Glee just orchestrates *who* does *what*, not *how* they do it.

## Agent Invocation Examples

### Codex

```bash
codex exec --json --full-auto "prompt"
```

| Flag | What it does |
|------|--------------|
| `exec` | Runs Codex in **agentic mode** (not just chat) |
| `--json` | Outputs structured JSONL for parsing |
| `--full-auto` | **No human confirmation** - Codex autonomously uses tools without asking |

With these flags, Codex will autonomously:
- Read files it needs
- Write/edit code
- Run shell commands
- Search the codebase
- Execute code to test things

### Claude Code

```bash
claude -p "prompt"
```

The `-p` flag runs Claude Code in non-interactive (print) mode.

### Gemini CLI

```bash
gemini -p "prompt"
```

## Debugging and Logging

### Stream Logs

Glee captures all agent stdout/stderr to `.glee/stream_logs/`:

```
.glee/stream_logs/
├── stdout-20250109.log    # Daily rotation
└── stderr-20250109.log
```

Use `tail -f .glee/stream_logs/stdout-*.log` to watch in real-time.

### Codex

Codex doesn't have a dedicated `--verbose` or `--debug` flag. Options for debugging:

1. **Use `--json`** - Outputs every event as newline-delimited JSON (tool calls, responses, everything)

2. **Configure in `~/.codex/config.toml`**:
   ```toml
   [telemetry]
   exporter = "file"  # or "none", "otlp"

   model_verbosity = "high"  # low | medium | high
   ```

3. **Output to file**:
   ```bash
   codex exec --json --full-auto "prompt" --output-last-message ./debug.txt
   ```

### Claude Code

```bash
claude -p "prompt" --verbose
```

### Gemini CLI

```bash
gemini -p "prompt" --verbosity=verbose
```

## References

- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference/)
- [Codex Config Docs](https://github.com/openai/codex/blob/main/docs/config.md)
