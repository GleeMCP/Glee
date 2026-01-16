# Open Responses API Specification

## Overview

Open Responses is an open-source specification for building multi-provider, interoperable LLM interfaces. It defines a shared schema and tooling layer that enables a unified experience for calling language models, streaming results, and composing agentic workflows.

- **Website:** https://openresponses.org
- **GitHub:** https://github.com/openresponses/openresponses
- **Spec:** https://openresponses.org/specification

## Background

Open Responses builds on OpenAI's Responses API (launched March 2025), which superseded the Chat Completions and Assistants APIs. It's designed for agentic workloads rather than turn-based conversations.

**Supported by:** OpenAI, Hugging Face, OpenRouter, Vercel, LM Studio, Ollama, vLLM

## Core Concepts

### Items

Items are the fundamental unit of context in Open Responses. They represent an atomic unit of model output, tool invocation, or reasoning state.

All items require three fields:

- `id`: Unique identifier
- `type`: Schema identifier (standard or prefixed with implementor slug like `acme:search_result`)
- `status`: Lifecycle state (`in_progress`, `completed`, `failed`, `incomplete`)

### Design Principles

- **Multi-provider by default**: One unified schema mapping to numerous model providers
- **Agentic workflow-friendly**: Consistent streaming events, tool invocation patterns
- **Stateless by default**: With support for encrypted reasoning
- **Extensible**: Stable core accommodating provider-specific features

## API Format

### Endpoint

```
POST /v1/responses
```

### Headers

```
Content-Type: application/json
Authorization: Bearer <token>
OpenResponses-Version: latest
```

### Basic Request

```json
{
  "model": "gpt-5.1-codex-mini",
  "instructions": "You are a helpful assistant.",
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": true,
  "store": false
}
```

### Request with Tools (Agentic Loop)

```json
{
  "model": "gpt-5.1-codex-mini",
  "input": "Find Q3 sales data and email a summary",
  "tools": [...],
  "max_tool_calls": 5,
  "tool_choice": "auto"
}
```

## Response Format

### Non-Streaming

Content-Type: `application/json`

### Streaming

Content-Type: `text/event-stream`

Events are JSON-encoded strings. Terminal event is the literal string `[DONE]`.

```json
{
  "event": "response.output_text.delta",
  "data": {
    "type": "response.output_text.delta",
    "sequence_number": 10,
    "item_id": "msg_07315d23...",
    "delta": " a"
  }
}
```

## Streaming Events

### Event Categories

**Delta Events:** Incremental changes

- `response.output_item.added`
- `response.output_text.delta`
- `response.reasoning.delta`

**State Machine Events:** Status transitions

- `response.in_progress`
- `response.completed`

### Streaming Lifecycle

1. `response.output_item.added` - Initiates an item
2. `response.content_part.added` - Begins streamable content
3. `response.<type>.delta` - Emits changes (repeated)
4. `response.<type>.done` - Closes content
5. `response.output_item.done` - Finalizes the item

## Tool Configuration

### `tool_choice` Parameter

| Value                                | Description                                        |
| ------------------------------------ | -------------------------------------------------- |
| `"auto"`                             | Model may call tools or respond directly (default) |
| `"required"`                         | Model must call at least one tool                  |
| `"none"`                             | Model must not invoke tools                        |
| `{"type": "function", "name": "fn"}` | Force specific tool                                |

### `allowed_tools` Parameter

Limits executable tools without removing them from context. Useful for prompt caching.

### Tool Types

- **External Tools**: Model invokes; developer executes and returns results
- **Internal Tools**: Provider executes within their system (e.g., web search, file search)

## Agentic Loop (Sub Agent Loops)

1. API receives user request and samples from model
2. If model emits tool call → API executes it
3. Tool results fed back to model for continued reasoning
4. Loop repeats until model signals completion

### Loop Control

- `max_tool_calls`: Cap iteration count
- `tool_choice`: Constrain invocable tools

## Advanced Parameters

| Parameter              | Description                                                  |
| ---------------------- | ------------------------------------------------------------ |
| `previous_response_id` | Resume prior response, loading its context                   |
| `truncation`           | `"auto"` (server may shorten) or `"disabled"` (fail instead) |
| `service_tier`         | Processing priority hints                                    |

## Error Handling

```json
{
  "type": "server_error",
  "code": "...",
  "param": "...",
  "message": "Human-readable explanation"
}
```

Error types: `server_error`, `invalid_request`, `not_found`, `model_error`, `too_many_requests`

## Codex API (ChatGPT Backend)

The ChatGPT Codex API uses a variant of the Responses API:

**Endpoint:** `https://chatgpt.com/backend-api/codex/responses`

**Required Parameters:**

- `instructions`: System prompt (required)
- `store`: Must be `false`
- `stream`: Must be `true`

**Available Models:**

- `gpt-5.1-codex-max`
- `gpt-5.1-codex-mini`
- `gpt-5.2`
- `gpt-5.2-codex`

**Example Request:**

```json
{
  "model": "gpt-5.1-codex-mini",
  "instructions": "You are a helpful assistant.",
  "input": [{ "role": "user", "content": "Hello" }],
  "store": false,
  "stream": true
}
```

**Headers:**

```
Authorization: Bearer <oauth_access_token>
Content-Type: application/json
ChatGPT-Account-Id: <account_id>  (if applicable)
```

## Comparison to Chat Completions

| Feature      | Chat Completions         | Open Responses            |
| ------------ | ------------------------ | ------------------------- |
| Design       | Turn-based conversations | Agentic workloads         |
| Tool calling | Basic function calling   | Native agentic loops      |
| Streaming    | Raw text/object deltas   | Semantic events           |
| State        | Stateful (Assistants)    | Stateless by default      |
| Output types | Text, JSON               | Text, images, JSON, video |

## References

- [OpenResponses.org](https://openresponses.org)
- [Specification](https://openresponses.org/specification)
- [Hugging Face Blog: Open Responses](https://huggingface.co/blog/open-responses)
- [GitHub Repository](https://github.com/openresponses/openresponses)
- [OpenAI Responses API Reference](https://platform.openai.com/docs/api-reference/responses)
