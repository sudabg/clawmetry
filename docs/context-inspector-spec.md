# Context Inspector — Feature Spec & Roadmap

**Author:** Dhriti (AI)  
**Date:** 2026-02-23  
**Status:** Draft  
**ClawMetry Version:** 0.9.16+

---

## 1. Problem Statement

When debugging AI agent behavior, the most critical question is: *"What did the agent actually see?"* Current ClawMetry transcript views show the conversation (user/assistant/tool messages) but don't break down the **full context window** — the system prompt, injected workspace files, memory files, tool definitions, and their individual token costs.

Competitors like Langfuse and Helicone offer prompt versioning and request inspection, but none provide a purpose-built view for **agent context composition** — understanding how system prompts, injected files, and runtime context combine to form the actual input.

## 2. What the Context Inspector Shows

### 2.1 Context Sections

For any session or individual LLM call, the inspector displays:

| Section | Source | Description |
|---------|--------|-------------|
| **System Prompt** | First `system` role message | The base personality/instructions |
| **Injected Files** | `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, etc. | Workspace context files loaded at session start |
| **Memory** | `memory/YYYY-MM-DD.md`, `MEMORY.md` | Daily notes and long-term memory |
| **Runtime Context** | Subagent instructions, MC task context | Dynamic context injected per-session |
| **Tool Definitions** | Tool schemas in the system message | Available tools and their descriptions |
| **Conversation History** | Prior user/assistant turns | Messages carried forward |
| **Tool Results** | Tool call outputs | Results from exec, browser, web_search, etc. |

### 2.2 Per-Section Token Breakdown

Each section shows:
- **Token count** (estimated via tiktoken or char-based heuristic)
- **Percentage of total context** (visual bar)
- **Character count** and approximate cost contribution
- **Diff from previous call** (context growth tracking)

### 2.3 Context Composition Visualization

A **stacked bar chart** showing how the context window fills up across turns:

```
Turn 1:  [████ system ██ files █ memory ░░░░░░░░░░░░░░░░░░] 12K / 200K
Turn 5:  [████ system ██ files █ memory ████ history ██ tools] 45K / 200K  
Turn 20: [████ system ██ files █ memory █████████████ history] 180K / 200K ⚠️
```

## 3. Integration with Existing Views

### 3.1 Session List (`/api/sessions`, `/api/transcripts`)

- Add a **"Context" column** showing peak context utilization (e.g., "67% of 200K")
- Add a **context icon** that opens the Context Inspector panel

### 3.2 Transcript Detail View (`/api/transcript/<session_id>`)

- New **"Context" tab** alongside the existing chat view
- Clicking any assistant message shows the context window at that point in time
- System messages are parsed and split into their component sections (using `## ` headers and known markers like "Project Context", "Subagent Context", "Runtime")

### 3.3 Transcript Events (`/api/transcript-events/<session_id>`)

- Add `context_snapshot` event type containing the parsed context breakdown
- Emit on first message and whenever context significantly changes (>10% growth)

## 4. UI Wireframe Description

### 4.1 Context Inspector Panel (right sidebar or modal)

```
┌─────────────────────────────────────────────┐
│ Context Inspector          Session: abc-123  │
│─────────────────────────────────────────────│
│ Total: 47,832 tokens (24% of 200K)          │
│                                              │
│ ▼ System Prompt              18,432 tk (39%) │
│   ████████████████████░░░░░░░░░░░░░░░░░░░░  │
│   > AGENTS.md                    3,200 tk    │
│   > SOUL.md                      2,100 tk    │
│   > USER.md                        850 tk    │
│   > TOOLS.md                     4,300 tk    │
│   > Runtime instructions         2,800 tk    │
│   > Tool definitions             5,182 tk    │
│   [View Full Text]                           │
│                                              │
│ ▼ Injected Project Context    8,200 tk (17%) │
│   ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│   > CODING.md                    3,100 tk    │
│   > memory/2026-02-23.md         2,400 tk    │
│   > MEMORY.md                    2,700 tk    │
│   [View Full Text]                           │
│                                              │
│ ▼ Conversation History       18,400 tk (38%) │
│   ████████████████████░░░░░░░░░░░░░░░░░░░░  │
│   12 user messages               6,200 tk    │
│   11 assistant messages         10,800 tk    │
│   [Expand]                                   │
│                                              │
│ ▼ Tool Results                2,800 tk  (6%) │
│   ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│   exec (3 calls)                 1,200 tk    │
│   web_search (1 call)            1,600 tk    │
│   [Expand]                                   │
│                                              │
│ ─── Context Growth Over Time ───             │
│   ▁▂▃▄▅▅▆▆▇▇██ (12 turns)                   │
└─────────────────────────────────────────────┘
```

### 4.2 Inline Context Badge (in transcript view)

Each assistant message gets a small badge: `ctx: 47K/200K (24%)` that expands on click.

### 4.3 Context Diff View

When comparing two turns, highlight what was added/removed from context (red/green diff style).

## 5. Implementation Approach

### 5.1 Data Sources

**Primary: Session JSONL files** (already used by `/api/transcript/<id>`)
- The first `system` role message contains the full context
- Parse known section markers to split into components
- OpenClaw system messages use identifiable headers:
  - `## Tooling` → tool definitions
  - `## Workspace` → workspace info
  - `## Runtime` → runtime context
  - `# Project Context` → injected files (with `## FILENAME.md` sub-headers)
  - `# Subagent Context` → subagent instructions

**Secondary: OTLP traces** (already received at `/v1/traces`)
- Token usage per call (input/output/total)
- Model info for accurate token counting

**Tertiary: Workspace files** (already accessed by `/api/memory-files`, `/api/file`)
- Current versions of AGENTS.md, SOUL.md, etc. for reference comparison

### 5.2 New API Endpoints

```
GET /api/context/<session_id>
    Returns parsed context breakdown for a session.
    Response: {
        sections: [{name, type, content, tokens, chars, percentage}],
        totalTokens, modelContextWindow, utilizationPct,
        perTurn: [{turn, totalTokens, sections: [...]}]
    }

GET /api/context/<session_id>/turn/<turn_number>
    Returns context snapshot at a specific turn.

GET /api/context/<session_id>/diff/<turn_a>/<turn_b>
    Returns diff between two turns' context.

GET /api/context/summary
    Returns context utilization stats across recent sessions
    (for overview dashboard card).
```

### 5.3 Token Estimation

- Use `tiktoken` if available (accurate for OpenAI models)
- Fallback: `len(text) / 3.5` character heuristic (reasonable for English)
- Cache token counts per session (context doesn't change retroactively)

### 5.4 System Message Parser

A new `_parse_system_context(system_msg: str) -> list[ContextSection]` function that:
1. Splits on known headers (`# Project Context`, `## AGENTS.md`, etc.)
2. Identifies tool definition blocks (JSON schemas)
3. Labels each section with type (system_prompt, injected_file, memory, tools, runtime)
4. Computes token estimates per section

### 5.5 Frontend

- Add a new tab/panel to the existing transcript detail modal (already in the HTML template ~line 7265)
- Use the existing CSS variable system and card styling
- Stacked bar via inline SVG or CSS (no new dependencies)
- Collapsible sections with syntax-highlighted content preview

## 6. Roadmap

### MVP (v0.10.0) — 2 weeks

- [ ] `_parse_system_context()` parser for OpenClaw system messages
- [ ] `GET /api/context/<session_id>` endpoint
- [ ] Token estimation (char-based heuristic)
- [ ] "Context" tab in transcript detail modal showing section breakdown with token counts
- [ ] Stacked bar visualization of context composition
- [ ] Context utilization badge on session list

### v1 (v0.11.0) — 4 weeks after MVP

- [ ] Per-turn context tracking (context growth over conversation)
- [ ] Context growth sparkline chart
- [ ] Turn-level `/api/context/<id>/turn/<n>` endpoint
- [ ] Diff view between turns
- [ ] `tiktoken` integration for accurate token counting
- [ ] Context utilization card on overview dashboard
- [ ] Alert rule: "context utilization > X%" (integrates with existing alert system)

### v2 (v0.12.0) — 8 weeks after MVP

- [ ] Context comparison across sessions (A/B prompt testing)
- [ ] Historical context size trends (integrate with HistoryDB)
- [ ] System prompt version tracking (detect when AGENTS.md/SOUL.md change)
- [ ] Token cost attribution per context section (using OTLP cost data)
- [ ] Export context snapshot as shareable JSON/markdown
- [ ] OTLP-native context metadata (custom span attributes for context sections)
- [ ] Recommendations engine: "Your TOOLS.md is 4,300 tokens — consider trimming unused tool docs"

## 7. Non-Goals (for now)

- **Prompt editing/management** — ClawMetry is observability, not a prompt IDE (Langfuse territory)
- **Context caching optimization** — that's the agent runtime's job
- **Multi-model context window comparison** — keep it simple, show one model's limits

## 8. Open Questions

1. Should context parsing be done server-side (Python) or client-side (JS)? **Recommendation:** Server-side — keeps the single-file app pattern and avoids shipping large system messages to the browser.
2. How to handle sessions where the system message isn't the first line in JSONL? **Recommendation:** Scan first 10 lines for `role: system`.
3. Should we store parsed context in a cache/DB or recompute on each request? **Recommendation:** MVP recomputes (fast enough for single sessions), v1 adds caching.

---

*This spec is a living document. Update as implementation progresses.*
