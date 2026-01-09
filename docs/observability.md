# Observability

Glee provides full observability into reviewer agent reasoning through real-time streaming and persistent SQLite logging.

## Real-time Streaming

When running reviews via MCP (`glee_review`) or CLI (`glee review`), the reviewer's reasoning process streams in real-time. This allows you to see what the agent is thinking as it analyzes your code.

### Watching Live Output

**Open a separate terminal and run:**

```bash
# Watch reviewer reasoning in real-time
tail -f .glee/stream.log
```

This works for both CLI and MCP (Claude Code) invocations. The stream log captures all reviewer output as it happens.

### CLI Usage

```bash
# CLI - streams output as reviewers work
glee review src/

# Multiple reviewers run in parallel for speed
# Output may interleave but is fully visible
```

### MCP Usage (Claude Code)

When using `glee_review` from Claude Code:

1. **MCP Log Notifications** - Glee sends `notifications/message` to Claude Code via the MCP protocol. If Claude Code displays these, you'll see reviewer output in the UI.

2. **Stream Log File** - Output is also written to `.glee/stream.log`. Use `tail -f` in another terminal:
   ```bash
   tail -f .glee/stream.log
   ```

The MCP notification approach uses `session.send_log_message()` from within the tool handler, which sends real-time updates through the MCP protocol.

## SQLite Logging

All agent outputs are automatically saved to SQLite in `.glee/glee.db`. This provides:

- **Full history** of all agent invocations
- **Queryable logs** for debugging and analysis
- **Scalability** - SQLite handles billions of rows

### Schema

```sql
CREATE TABLE IF NOT EXISTS agent_logs (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    prompt TEXT NOT NULL,
    output TEXT,          -- Final/parsed output
    raw TEXT,             -- Raw subprocess output (full reasoning)
    error TEXT,
    exit_code INTEGER,
    duration_ms INTEGER,
    success INTEGER
)
```

### Where Logging Happens

**`glee/agents/base.py:294-305`** - in `_run_subprocess_streaming()`:

```python
# Log to SQLite
agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
if agent_logger:
    run_id = agent_logger.log(
        agent=self.name,
        prompt=prompt,
        output=output,
        raw=output,
        error=error if (process.returncode != 0 or timed_out) else None,
        exit_code=process.returncode if not timed_out else -1,
        duration_ms=duration_ms,
    )
```

**`glee/logging.py:38-83`** - the `AgentRunLogger.log()` method:

```python
def log(
    self,
    agent: str,
    prompt: str,
    output: str | None = None,
    raw: str | None = None,
    error: str | None = None,
    exit_code: int = 0,
    duration_ms: int | None = None,
) -> str:
    log_id = str(uuid4())[:8]
    self.conn.execute(
        """
        INSERT INTO agent_logs
        (id, timestamp, agent, prompt, output, raw, error, exit_code, duration_ms, success)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            log_id,
            datetime.now().isoformat(),
            agent,
            prompt,
            output,
            raw,
            error,
            exit_code,
            duration_ms,
            1 if exit_code == 0 and error is None else 0,
        ],
    )
    self.conn.commit()
    return log_id
```

## CLI Commands

### List Agent Runs

```bash
# Show recent agent invocations
glee logs agents

# Filter by agent
glee logs agents --agent claude

# Show only successful runs
glee logs agents --success-only
```

### View Run Details

```bash
# View full details of a specific run
glee logs detail <run-id>

# Include raw output
glee logs detail <run-id> --raw
```

### Application Logs

```bash
# Show application logs
glee logs show

# Filter by level
glee logs show --level ERROR

# Search in messages
glee logs show --search "review"

# Get log statistics
glee logs stats
```

## Direct Database Access

You can also query the SQLite database directly:

```bash
# Open database
sqlite3 .glee/glee.db

# Recent reviews
SELECT id, timestamp, agent, duration_ms, success
FROM agent_logs
ORDER BY timestamp DESC
LIMIT 10;

# Failed runs
SELECT * FROM agent_logs WHERE success = 0;

# Average duration by agent
SELECT agent, AVG(duration_ms) as avg_ms
FROM agent_logs
GROUP BY agent;
```

## Architecture

```
User runs glee_review (MCP) or glee review (CLI)
    |
    v
Reviewers run in parallel (ThreadPoolExecutor)
    |
    +---> Each reviewer uses _run_subprocess_streaming()
    |         |
    |         +---> Streams output to stderr (real-time visibility)
    |         |
    |         +---> Captures full output
    |         |
    |         +---> Logs to SQLite via AgentRunLogger.log()
    |
    v
Results returned to user (MCP response or CLI summary)
```
