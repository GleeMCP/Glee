# Review Feedback System Design

## Overview

Glee's review system provides structured code review feedback from configured reviewers. The main agent (the one the user talks to) writes code, and reviewers provide feedback using **severity levels** to help users prioritize what to fix.

## Simplified Model

```
Main Agent (user's agent, e.g., Claude Code)
    │
    │ writes code
    ▼
Reviewer (primary: codex, secondary: gemini)
    │
    │ returns structured feedback
    ▼
User decides what to apply
```

**Key principles:**
- The main agent handles coding - no separate "coder" role
- One reviewer at a time (primary first)
- User can request a second opinion (secondary reviewer)
- Maximum 2 reviewers per review cycle
- User always decides what feedback to apply

## Review Severity Levels

### Opinion Levels

| Level | Meaning | Priority |
|-------|---------|----------|
| MUST | Required change - critical issue | High |
| SHOULD | Recommended change - improvement | Medium |

### Issue Priority Levels

| Level | Meaning | Priority |
|-------|---------|----------|
| HIGH | Critical issue - security, correctness | High |
| MEDIUM | Moderate issue - performance, maintainability | Medium |
| LOW | Minor issue - style, naming | Low |

## Review Output Format

Reviewers structure their feedback using severity tags:

```
[MUST] Fix SQL injection vulnerability in query builder
[MUST] Add authentication check before accessing user data
[HIGH] Memory leak in connection pool - objects never released
[SHOULD] Consider using async/await for I/O operations
[MEDIUM] Function exceeds 50 lines, consider splitting
[LOW] Variable 'x' could have more descriptive name
```

## Review Flow

### Standard Flow

```
User: "Review my code"
         ↓
Glee invokes primary reviewer (e.g., codex)
         ↓
Reviewer returns structured feedback
         ↓
User sees feedback with severity levels
         ↓
User decides:
  a) Apply all - fix everything
  b) Apply HIGH/MUST only - fix critical issues
  c) Discard - ignore feedback
  d) Second opinion - get another reviewer's take
```

### Second Opinion Flow

```
User requests second opinion
         ↓
Glee invokes secondary reviewer (e.g., gemini)
         ↓
User sees both feedbacks side by side
         ↓
User decides what to apply from each
```

## Configuration

```yaml
# .glee/config.yml

project:
  id: uuid
  name: project-name

reviewers:
  primary: codex    # Default reviewer (required)
  secondary: gemini # For second opinions (optional)
```

## CLI Commands

```bash
# Set reviewers
glee config set reviewer.primary codex
glee config set reviewer.secondary gemini

# Clear secondary
glee config unset reviewer.secondary

# View config
glee config get

# Run review
glee review src/                     # Review with primary
glee review src/ --second-opinion    # Also get secondary review

# View status
glee status                          # Shows reviewer configuration
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `glee_review` | Run review with primary reviewer |
| `glee_config_set` | Set config value (e.g., reviewer.primary) |
| `glee_config_unset` | Unset config value (e.g., reviewer.secondary) |
| `glee_status` | Show reviewer configuration |

## Data Flow

```
┌──────────────┐    code      ┌──────────────┐   structured   ┌──────────┐
│  Main Agent  │ ────────────►│   Reviewer   │ ──────────────►│   User   │
│ (writes code)│              │ (codex/etc)  │    feedback    │ (decides)│
└──────────────┘              └──────────────┘                └──────────┘
                                                                   │
                                              ┌────────────────────┼────────────────────┐
                                              ▼                    ▼                    ▼
                                        ┌──────────┐        ┌──────────┐        ┌──────────┐
                                        │  Apply   │        │ Discard  │        │  Second  │
                                        │ feedback │        │ feedback │        │ opinion  │
                                        └──────────┘        └──────────┘        └──────────┘
```

## Implementation Status

### Done
- [x] Single reviewer flow (primary reviewer)
- [x] Structured feedback with severity levels
- [x] CLI commands for reviewer management
- [x] MCP tools for Claude Code integration

### TODO
- [ ] Second opinion flag (`--second-opinion`)
- [ ] Side-by-side feedback comparison UI
- [ ] Feedback history and tracking
