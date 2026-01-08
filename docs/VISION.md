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

Glee is the **Orchestration Hub for AI Coding Agents**.

Not a replacement. A multiplier.

```
Without Glee:
┌─────────────┐
│   Agent     │ → Works alone, no memory, no checks
└─────────────┘

With Glee:
┌─────────────┐     ┌─────────────┐
│   Agent A   │ ←→  │    Glee     │ ←→ │   Agent B   │
└─────────────┘     │  - Memory   │     └─────────────┘
                    │  - Review   │
                    │  - Knowledge│
                    └─────────────┘
```

## Three Pillars

### 1. Intelligent Review Protocol

Agents make mistakes. Code gets shipped with bugs, security holes, and anti-patterns.

Glee provides structured, professional code review:

- Curated review checklists by language and framework
- Security, performance, and maintainability standards
- Structured feedback that agents can act on
- Iteration loops until quality gates pass

**Not "does this code look okay?" — but systematic quality assurance.**

### 2. Agent Abstraction Layer

Today you use Claude Code. Tomorrow maybe Codex is better for your use case. Next month, a new player emerges.

Glee abstracts the underlying agent:

- Unified interface across all coding agents
- Mix and match: Claude writes, Codex reviews, Gemini audits
- Switch agents without losing context
- Best tool for each job

**Use any agent. Use all agents. Glee orchestrates.**

### 3. Persistent Memory

This is the biggest gap in today's coding agents.

Glee remembers everything:

- **Project memory**: Architecture decisions, conventions, tech stack choices
- **Review memory**: Past issues, common mistakes, what worked
- **Team memory**: Who owns what, style preferences, tribal knowledge
- **Learning**: Gets smarter about your codebase over time

Every agent you use can tap into this shared memory.

**The more you use Glee, the better every agent becomes at understanding your project.**

## The Flywheel

```
More Usage → More Memory → Better Reviews → Better Code → More Usage
```

This is the moat. Every review, every decision, every fix makes Glee smarter about your project. This knowledge compounds. It can't be replicated by switching to a new tool.

## Design Principles

### 1. Orchestrator, Not Competitor

We don't replace coding agents. We coordinate them. When Claude Code ships a new feature, Glee users benefit immediately.

### 2. Agent Agnostic

No lock-in to any single agent. Glee works with Claude Code, Codex, Gemini CLI, Cursor, and whatever comes next.

### 3. Local First

Your code stays on your machine. Agents run locally with full capabilities. Memory can be local or synced.

### 4. Zero Config Start

`uvx glee` and you're running. Complexity is opt-in, not required.

### 5. Open Core

The orchestration layer is open source. Build on it, extend it, trust it.

## V1: The Starting Point

The first version focuses on the core loop:

**"Get a second opinion on your code from another AI agent."**

- Works with Claude Code out of the box
- Uses Codex (or configurable) for review
- Simple approve/iterate loop
- File-based storage (no database required)
- Installs in one command

This is intentionally minimal. But it establishes the pattern: your agent + Glee = better code.

## The Future

### V2: Memory Layer

- Vector database for project knowledge
- Automatic context injection
- Learn from every review

### V3: Multi-Agent Workflows

- Define custom agent pipelines
- Specialized agents for security, performance, testing
- Human-in-the-loop checkpoints

### V4: Team & Enterprise

- Shared memory across team
- GitHub/GitLab integration
- Audit logs and compliance
- SSO and access control

### V5: Knowledge Marketplace

- Share review checklists
- Import best practices
- Community-contributed agent configs

## Why "Glee"?

A glee club is a group of voices singing in harmony. No single voice dominates — each contributes its unique part to create something greater than any could alone.

That's what we're building: a harmonious collaboration between AI agents, each contributing their strengths, coordinated into beautiful code.

---

_Glee: The Conductor for Your AI Orchestra._
