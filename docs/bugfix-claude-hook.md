# Bugfix: Claude Code SessionEnd Hook Issues

**Date:** 2026-01-10
**Affected:** `glee summarize-session` via SessionEnd hook

## Bug 1: Stdin Race Condition

### Symptom
SessionEnd hook intermittently received 0 bytes on stdin, causing session summarization to fail silently.

```
[2026-01-10T20:42:06.625643] summarize-session started with --from=claude
[2026-01-10T20:42:06.626351] Read stdin: 0 bytes
[2026-01-10T20:42:06.626397] No transcript_path in stdin
```

### Root Cause
The original hook command used backgrounding with `nohup ... &`:

```bash
tmp=$(mktemp) && cat > "$tmp" && (nohup glee summarize-session --from=claude < "$tmp" >/dev/null 2>&1; rm -f "$tmp") >/dev/null 2>&1 &
```

When Claude Code exits, it may close stdin before `cat` can fully read the data. The race condition caused intermittent failures where stdin was empty or contained only partial data.

### Fix
Changed to synchronous execution:

```bash
glee summarize-session --from=claude 2>/dev/null || true
```

**Trade-off:** Claude Code waits ~2-3 seconds for summarization to complete before fully exiting. This is acceptable for reliability.

**File changed:** `glee/config.py` (hook registration)

---

## Bug 2: Recursive Session Creation

### Symptom
Multiple summarization sessions were created in rapid succession, with recursively nested prompts:

```
"Analyze this coding session...
  User: Analyze this coding session...
    User: Analyze this coding session...
```

Log showed many 2-message sessions being processed:
```
[2026-01-10T20:56:07.369220] Conversation has 2 messages
[2026-01-10T20:56:12.176406] Conversation has 2 messages
[2026-01-10T20:56:16.897719] Conversation has 2 messages
...
```

### Root Cause
1. User exits session → SessionEnd hook fires
2. `glee summarize-session --from=claude` invokes Claude CLI
3. Claude CLI creates a **new session** to generate the summary
4. When that session ends → **another SessionEnd hook fires**
5. This creates a cascade of summarization attempts

Each summarization session would trigger another hook, leading to infinite recursion (bounded only by eventual failures).

### Fix
Added `--no-session-persistence` flag to Claude CLI invocation:

```python
args = [
    self.command,
    "-p", prompt,
    "--output-format", "text",
    "--no-session-persistence",  # Prevent hooks from firing for this session
]
```

This prevents the summarization session from being persisted, which prevents SessionEnd hooks from triggering.

**File changed:** `glee/agents/claude.py`

---

## Summary of Changes

| File | Change |
|------|--------|
| `glee/config.py` | Simplified hook to synchronous execution |
| `glee/agents/claude.py` | Added `--no-session-persistence` flag |

## Verification

After fixes, summarization works reliably:
```
[2026-01-10T21:14:51.816921] summarize-session started with --from=claude
[2026-01-10T21:14:51.817886] Read stdin: 292 bytes
[2026-01-10T21:14:51.818236] Conversation has 7 messages
[2026-01-10T21:14:59.756672] summarize-session completed successfully
```
