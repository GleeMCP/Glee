# Glee TODO

## Design Principle: Configurable Autonomy

Different users, different needs. Not everyone can or wants to make every decision.

```
Human         = Conductor (directs, decides) — or delegates
Main Agent    = Principal musician (does the work)
Subagents     = Session musicians (called in as needed)
Glee          = Stage manager (logistics, coordination, memory)
```

### Autonomy Levels

| Level        | Who Decides                                 | Best For                    |
| ------------ | ------------------------------------------- | --------------------------- |
| `full_hitl`  | Human approves every step                   | Control freaks, learning    |
| `guided`     | AI suggests, human approves major decisions | Most engineers (default)    |
| `autonomous` | AI drives, human reviews at end             | Vibe coders, busy engineers |

```yaml
# .glee/config.yml
autonomy:
  level: guided # full_hitl | guided | autonomous

  # Fine-grained controls (optional)
  auto_apply_review: false # Auto-apply reviewer suggestions
  auto_spawn_subagents: true # Let main agent spawn helpers without asking
  require_approval_for:
    - commit
    - deploy
    - delete
```

### Guardrails (all levels)

- Always show what AI is doing (transparency)
- Never auto-commit/deploy without explicit config
- Log all decisions for audit

### Observability

MCP servers can't pass stderr to clients - logs disappear into void.

**Solution: Stream logging to files**

- [x] Log agent stdout/stderr to `.glee/stream_logs/`
- [x] Daily rotation: `stdout-YYYYMMDD.log`, `stderr-YYYYMMDD.log`
- [ ] Add OpenTelemetry integration
- [ ] Web dashboard or TUI viewer for real-time monitoring

### Development Philosophy

- **No backward compatibility concerns** - nobody uses this yet
- Break things freely, redesign from scratch if needed
- Ship fast, iterate faster

---

## 1. Subagent Parallel Execution

Subagents are for **small, scoped tasks** that can run in parallel - not for opinionated work like reviews.

### Use Cases

- Read multiple files in parallel
- Web searches in parallel
- Fix typos across multiple files in parallel
- Run linters/formatters in parallel
- Fetch documentation from multiple sources

### Implementation

- [ ] Define subagent interface (input → output, no side conversations)
- [ ] Spawn multiple subagents concurrently
- [ ] Aggregate results back to main agent
- [ ] Handle timeouts and failures gracefully
- [ ] Cap max concurrent subagents (resource limits)
- [ ] Progress reporting for long-running parallel tasks

## 2. Memory Testing & Optimization

- [ ] Add unit tests for Memory CRUD (add/search/delete/clear)
- [ ] Test with stubbed embedder to avoid slow model loading in tests
- [ ] Test category filtering and semantic search accuracy
- [ ] Benchmark search performance with large memory stores
- [ ] Consider caching frequent queries

## 3. Architecture Refactor: Simplify Agent Model ✅ DONE

### Problem (Solved)

~~Current role-based model is confusing:~~

- ~~Multiple "coders" - but which one is primary?~~
- ~~Multiple "reviewers" - what if they conflict?~~
- ~~"coder" role is redundant (the main agent IS the coder)~~

### Current Model

```
Main Agent (the one user talks to) = handles coding
    └── Reviewers (configured preferences)
        ├── primary: codex (default)
        └── secondary: gemini (optional, for second opinions)
```

### Implemented Changes

- [x] Remove "coder" role entirely - main agent handles coding
- [x] Simplify `.glee/config.yml`:

  ```yaml
  project:
    id: ...
    name: ...

  reviewers:
    primary: codex # Default reviewer
    secondary: gemini # For second opinions (optional)
  ```

- [x] Update CLI: `glee config set/unset/get`
- [x] Update MCP server to use new model
- [x] Update `glee review` to use primary reviewer

### Review Flow (User-Controlled)

```
1. Run review → ONE reviewer returns feedback
2. User decides:
   a) Discard - ignore the feedback
   b) Apply - modify code based on feedback
   c) Second opinion - ask another reviewer (max 2 total)
3. If second opinion requested:
   - Show both feedbacks
   - User decides what to apply
```

- [x] Implement single-reviewer-at-a-time flow
- [ ] Add "request second opinion" action in CLI
- [x] Cap at 2 reviewers max (primary + secondary)
- [ ] UI to show/compare both reviewer feedbacks

### Agent2Agent (A2A) protocol

- [ ] Research A2A protocol specification
- [ ] Implement A2A server alongside MCP server

## Future Ideas

- [ ] Agent specialization by file type/domain (spawn rust expert for .rs files)
- [ ] Learning from review outcomes (which reviewer catches more issues?)
- [ ] Integration with CI/CD (run glee review in pipelines)
