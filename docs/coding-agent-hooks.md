# Coding Agent Hooks Comparison

A comprehensive comparison of hook systems across AI coding agents. This informs Glee's session continuity design.

## Summary Table

| Agent | Hook System | Config Location | Hook Events | Session End Hook |
|-------|-------------|-----------------|-------------|------------------|
| **Claude Code** | Native | `~/.claude/settings.json`, `.claude/settings.json` | 6 events | `Stop` |
| **Cursor** | Native | `~/.cursor/hooks.json`, `.cursor/hooks.json` | 10+ events | `stop` |
| **Gemini CLI** | Native | `~/.gemini/settings.json`, `.gemini/settings.json` | 11 events | `SessionEnd` |
| **OpenCode** | Plugin-based | `.opencode/plugin/`, `opencode.json` | Event streaming | `session.idle` |
| **Codex CLI** | Limited (notify) | `~/.codex/config.toml` | 2 events | `agent-turn-complete` |
| **Antigravity** | Workflows/Rules | `.agent/workflows/`, `.agent/rules/` | N/A (different model) | N/A |

---

## Claude Code

**Documentation:** [Claude Code Hooks](https://code.claude.com/docs/en/hooks)

### Hook Events

| Event | When | Can Block | Use Case |
|-------|------|-----------|----------|
| `SessionStart` | Session starts (startup/resume/clear) | No | **Load context, warmup** |
| `PreToolUse` | Before tool execution | Yes | Validate, block dangerous ops |
| `PostToolUse` | After tool completion | No | Format, lint, log |
| `Notification` | On notifications | No | Custom alerts |
| `Stop` | Agent stops/completes | No | **Session summarization** |
| `UserPromptSubmit` | User submits prompt | No | Inject per-message context |
| `PermissionRequest` | Permission dialog shown | Yes | Auto-approve/deny |

### Configuration

```json
// ~/.claude/settings.json or .claude/settings.json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "glee summarize-session --background"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "glee warmup"
          }
        ]
      }
    ]
  }
}
```

### Exit Codes

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Success | stdout shown to user (or injected for SessionStart/UserPromptSubmit) |
| 2 | Blocking error | stderr fed back to Claude for processing |

### Key for Glee

- `SessionStart`: Inject warmup context when session starts
- `Stop`: Trigger session summarization
- stdout from hooks is injected into context (perfect for warmup)

---

## Cursor

**Documentation:** [Cursor Hooks](https://cursor.com/docs/agent/hooks)

### Hook Events

**Agent Hooks:**
| Event | When | Permission-based |
|-------|------|------------------|
| `beforeShellExecution` | Before shell command | Yes |
| `afterShellExecution` | After shell command | No |
| `beforeMCPExecution` | Before MCP tool | Yes |
| `afterMCPExecution` | After MCP tool | No |
| `beforeReadFile` | Before file read | Yes |
| `afterFileEdit` | After file edit | No |
| `beforeSubmitPrompt` | Before prompt submission | Yes |
| `afterAgentResponse` | After agent response | No |
| `afterAgentThought` | After agent reasoning | No |
| `stop` | Agent completes | No |

**Tab Hooks:**
| Event | When |
|-------|------|
| `beforeTabFileRead` | Before Tab reads file |
| `afterTabFileEdit` | After Tab edits file |

### Configuration

```json
// .cursor/hooks.json or ~/.cursor/hooks.json
{
  "version": 1,
  "hooks": {
    "stop": [
      { "command": "./hooks/session-end.sh" }
    ],
    "beforeSubmitPrompt": [
      { "command": "./hooks/warmup.sh" }
    ]
  }
}
```

### Input/Output

Hooks receive JSON via stdin with:
- `conversation_id`, `generation_id`, `model`
- `hook_event_name`, `cursor_version`
- `workspace_roots`, `user_email`

Permission hooks return:
```json
{
  "permission": "allow" | "deny" | "ask",
  "user_message": "optional message to user",
  "agent_message": "optional message to agent"
}
```

### Key for Glee

- `beforeSubmitPrompt`: Inject warmup context
- `stop`: Trigger session summarization
- Rich metadata available (conversation_id, workspace info)

---

## Gemini CLI

**Documentation:** [Gemini CLI Hooks](https://geminicli.com/docs/hooks/)

### Hook Events

| Event | When | Use Case |
|-------|------|----------|
| `SessionStart` | Session begins | **Load context, warmup** |
| `SessionEnd` | Session ends | **Save state, summarize** |
| `BeforeAgent` | Before agent loop | Add context, validate |
| `AfterAgent` | After agent loop | Review output |
| `BeforeModel` | Before LLM call | Modify prompts |
| `AfterModel` | After LLM response | Filter responses |
| `BeforeToolSelection` | Before tool selection | Filter available tools |
| `BeforeTool` | Before tool execution | Validate args, block |
| `AfterTool` | After tool execution | Process results |
| `PreCompress` | Before context compression | Save state |
| `Notification` | On notifications | Auto-approve, log |

### Configuration

```json
// ~/.gemini/settings.json or .gemini/settings.json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "name": "glee-warmup",
            "type": "command",
            "command": "glee warmup",
            "timeout": 30000
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "name": "glee-summarize-session",
            "type": "command",
            "command": "glee summarize-session --background"
          }
        ]
      }
    ]
  }
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Allow/success |
| 2 | Deny/block |

### Key for Glee

- `SessionStart`: Perfect for warmup injection
- `SessionEnd`: Perfect for session summarization
- Most explicit session lifecycle hooks of all agents

---

## OpenCode

**Documentation:** [OpenCode Extensibility](https://dev.to/einarcesar/does-opencode-support-hooks-a-complete-guide-to-extensibility-k3p)

### Extensibility Model

OpenCode uses a plugin-based system rather than simple hooks:

| Mechanism | Complexity | Use Case |
|-----------|------------|----------|
| Plugin System | High | Event hooks, validations |
| SDK/API | Medium | Programmatic control |
| MCP Servers | Medium | Tool integration |
| Custom Commands | Low | Reusable prompts |
| Non-Interactive Mode | Low | CI/CD, batch |

### Plugin Events

```typescript
// .opencode/plugin/my-plugin.ts
export default {
  tool: {
    execute: {
      before: async (input, output) => { /* pre-tool */ },
      after: async (input, output) => { /* post-tool */ }
    }
  },
  event: async ({ event }) => {
    if (event.type === 'session.idle') {
      // Session completed
    }
  }
}
```

### Configuration

```json
// opencode.json
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": {
    "glee-integration": {
      "enabled": true
    }
  }
}
```

### Key for Glee

- `session.idle` event for session end
- Plugin system allows richer integration
- MCP servers provide tool-level hooks

---

## Codex CLI (OpenAI)

**Documentation:** [Codex Advanced Config](https://developers.openai.com/codex/config-advanced/)

### Event System (Limited)

Codex has a notification system rather than full hooks:

| Feature | Events | Use Case |
|---------|--------|----------|
| `notify` | `agent-turn-complete` | External notifications |
| `tui.notifications` | `agent-turn-complete`, `approval-requested` | TUI alerts |

### Configuration

```toml
# ~/.codex/config.toml

# External notification command
notify = ["python3", "/path/to/notify.py"]

# Or simple sound
notify = ["bash", "-lc", "afplay /System/Library/Sounds/Blow.aiff"]

# TUI notifications (built-in)
[tui]
notifications = ["agent-turn-complete", "approval-requested"]
```

### Notify Script Input

Scripts receive JSON with:
- `type`: Event type
- `thread-id`, `turn-id`
- `cwd`: Working directory
- `input-messages`: Conversation messages
- `last-assistant-message`: Final response

### OpenTelemetry Events

For deeper observability, Codex exports OTEL events:
- `codex.conversation_starts`
- `codex.api_request`
- `codex.tool_decision`
- `codex.tool_result`

### Key for Glee

- `notify` with `agent-turn-complete` is the session-end hook
- No session-start hook (limitation)
- Would need to use MCP for warmup injection

---

## Antigravity (Google)

**Documentation:** [Getting Started with Antigravity](https://codelabs.developers.google.com/getting-started-google-antigravity)

### Model

Antigravity uses a different paradigm: **Workflows** and **Rules** instead of hooks.

### Workflows

Saved prompts triggered with `/` commands:

```
# .agent/workflows/session-start.md
---
name: Session Start
description: Load context and show status
---

Run glee warmup and show me where we left off.
```

**Locations:**
- Project: `.agent/workflows/`
- Global: `~/.gemini/antigravity/global_workflows/`

### Rules

Persistent guidelines for agent behavior:

```
# .agent/rules/glee.md
---
name: Glee Integration
---

At the start of each session, use the glee_warmup MCP tool.
Before ending, use glee_summarize_session to save context.
```

**Locations:**
- Project: `.agent/rules/`
- Global: `~/.gemini/GEMINI.md`

### Agent Control

| Setting | Options |
|---------|---------|
| Terminal Execution | Off, Auto, Turbo |
| Allow/Deny Lists | Command filtering |
| Browser Allowlist | URL restrictions |

### Key for Glee

- No programmatic hooks—workflow/rules based
- Integration via MCP tools + rules that instruct agent to call them
- Less deterministic than hook-based systems

---

## Glee Integration Strategy

### Universal Hooks

For session continuity, Glee needs to hook into:

| Agent | Session Start | Session End |
|-------|---------------|-------------|
| Claude Code | `SessionStart` | `Stop` |
| Cursor | `beforeSubmitPrompt` | `stop` |
| Gemini CLI | `SessionStart` | `SessionEnd` |
| OpenCode | Plugin event | `session.idle` |
| Codex CLI | MCP (no hook) | `notify` with `agent-turn-complete` |
| Antigravity | Rules/Workflows | Rules/Workflows |

### Recommended Implementation

1. **`glee warmup`** — CLI command that outputs context to stdout
   - Called by session-start hooks
   - Output injected into agent context

2. **`glee summarize-session`** — CLI command that summarizes session
   - Called by session-end hooks with `--background` flag
   - Reads git diff, creates session summary in memory

3. **MCP Tools** — For agents without hooks
   - `glee_warmup` — Called explicitly or via rules
   - `glee_summarize_session` — Called explicitly

### Hook Installation

```bash
# Install hooks for all supported agents
glee hooks install

# Install for specific agent
glee hooks install --agent claude-code
glee hooks install --agent cursor
glee hooks install --agent gemini-cli
```

This would modify the appropriate config files for each agent.

---

## Sources

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Cursor Hooks Documentation](https://cursor.com/docs/agent/hooks)
- [Gemini CLI Hooks](https://geminicli.com/docs/hooks/)
- [OpenCode Extensibility Guide](https://dev.to/einarcesar/does-opencode-support-hooks-a-complete-guide-to-extensibility-k3p)
- [Codex CLI Advanced Configuration](https://developers.openai.com/codex/config-advanced/)
- [Getting Started with Google Antigravity](https://codelabs.developers.google.com/getting-started-google-antigravity)
- [Cursor Hooks Partners Announcement](https://cursor.com/blog/hooks-partners)
- [GitHub: Codex Hooks Discussion](https://github.com/openai/codex/discussions/2150)
