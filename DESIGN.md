# Bookly Support Agent — Design Document

## Architecture Overview

The agent uses a **ReAct (Reason + Act) loop** built on Anthropic's Claude API
with native tool use. Each customer message is processed through a persistent
conversation history alongside a system prompt that encodes Bookly's business
logic — functionally equivalent to Decagon's Agent Operating Procedures (AOPs).

**Request Flow:**
```
Customer Message
      ↓
System Prompt + Full Conversation History
      ↓
Claude (claude-sonnet-4-6) — reasons about intent and next action
      ↓
Tool call requested?
  YES → Execute tool → Append result to history → Loop back to Claude
  NO  → Generate final text response → Return to customer
```

**Why a Loop Rather than a Single LLM Call:**
A single API call can only produce one output. Some requests require sequential
tool calls — for example, a return request may require checking an order status
before initiating the return. The ReAct loop handles this naturally: each iteration
is one reasoning step, and the agent continues until it has everything it needs
to give a complete response.

**Components:**
- `prompts.py` — System prompt encoding all business rules (the AOP layer)
- `tools.py` — Mock tool functions: order lookup, return processing, policy retrieval
- `agent.py` — ReAct loop orchestrating Claude API calls and tool execution
- `app.py` — Flask web server managing sessions and routing
- `static/index.html` — Lightweight chat UI

**Implemented Tools:**
1. `get_order_status(order_id)` — Looks up order status, tracking number, and delivery estimate
2. `process_return_request(order_id, reason, items)` — Initiates return with eligibility check
3. `lookup_policy(policy_type)` — Retrieves shipping, returns, and password reset policies

---

## Conversation & Decision Design

**Intent Recognition**
Intent is handled implicitly by Claude's reasoning rather than a separate
classifier. Given the narrow domain (order support), Claude reliably infers
intent from free-form text without an additional classification step — reducing
system complexity without meaningful accuracy loss.

**Decision Branches** encoded in the system prompt:

| Situation | Agent Behavior | Why |
|-----------|---------------|-----|
| Order question, no order ID provided | Ask for order ID before calling tool | Prevents tool call failure from missing required parameter |
| Order question with order ID | Call `get_order_status` immediately | Tool is source of truth — agent never guesses status |
| Return request, all info present | Call `process_return_request` | All preconditions met, safe to act |
| Return request, info missing | Ask follow-up questions across turns | Collects order ID, reason, and items incrementally |
| Policy question | Call `lookup_policy` with category | Prevents agent citing stale or hallucinated policy details |
| Frustration or out-of-scope request | Escalate with `[ESCALATE]` tag | Structured signal for human handoff routing |

**Why Collect All Parameters Before Acting:**
The system prompt instructs the agent to gather all required information before
calling a tool. Attempting a tool call with missing parameters causes a failure.
More importantly, it mirrors how production AOP workflows define preconditions:
a return workflow only executes when identity, order ID, and return reason are
all confirmed. The agent's multi-turn collection behavior demonstrates this
pattern at a conversational level.

**Why Business Rules Live in Tool Code vs. The Prompt:**
The prompt is natural language — it can be misinterpreted, edge-cased around,
or simply ignored under unusual inputs. Business rules with real consequences
(like return eligibility) live in the tool code as hard logic. For example,
`process_return_request` rejects returns for orders still in "processing" status
regardless of what the prompt says. This mirrors the architecture where CX
teams author AOP logic in natural language, but engineers implement the
guardrails beneath it that the language layer cannot override.

---

## Example System Prompt
```
You are Bookly's customer support AI agent. You help customers with order
inquiries, returns, and general questions about policies.

## Your Identity
- You resolve issues completely — you don't just answer questions, you take action
- You never make up information. If you don't know something, say so and escalate

## Decision Rules

### Order Status Inquiries
- ALWAYS call get_order_status before responding to any order question
- If the customer hasn't provided an order ID, ask for it before calling the tool
- Never guess or estimate order status — always use the tool

### Return Requests
- Before initiating a return, collect: order ID, reason, and which items to return
- If any of these are missing, ask follow-up questions before acting
- Once you have all three, call process_return_request
- Never confirm a return before calling the tool — the tool determines eligibility

### Policy Questions
- Use lookup_policy for shipping, returns, and password reset questions
- Do not quote specific details from memory — always retrieve from the tool

### Escalation
- Escalate when: suspected fraud, unresolved frustration, out-of-scope request
- Say: "Let me connect you with a member of our support team. [ESCALATE]"

## Guardrails
- Never invent order IDs, tracking numbers, or return confirmation numbers
- Stay focused on Bookly customer support topics only
```

**Why This Prompt Structure Works:**
Each section maps to a specific failure mode it's designed to prevent. "ALWAYS
call get_order_status" prevents the agent from estimating status from context.
"Never confirm a return before calling the tool" prevents false expectations
when a return is ineligible. The escalation tag `[ESCALATE]` is a structured
signal a production backend would detect and route — not just a conversational
courtesy. Tone instructions are placed last because they are the lowest priority
constraint: they refine how the agent communicates, not what it does.

---

## Hallucination & Safety Controls

**Three Guardrail Layers:**

**1. Prompt-Level**
The system prompt explicitly forbids inventing order IDs, tracking numbers,
or return confirmation numbers. The agent is instructed to surface only
information retrieved from tools, never from its own training knowledge.
This addresses the most common CX agent failure: confidently providing
wrong order details.

**2. Tool-Enforced Business Rules**
Eligibility logic lives in code, not the prompt. For example, `process_return_request`
checks order status and rejects returns for orders still in "processing"
regardless of what the natural language layer instructs. The tool is the
last line of defense — it enforces rules that have financial consequences
and cannot be overridden by prompt manipulation or edge-case inputs.

**3. Structured Escalation**
Explicit conditions in the system prompt trigger human handoff: suspected
fraud, unresolved frustration, out-of-scope requests. The `[ESCALATE]` tag
is a structured signal that a production backend would route to a human
agent queue. In a real deployment this would trigger a ticket creation,
queue assignment, and conversation summary handoff — the agent's last
action before stepping aside.

---

## Production Readiness — Tradeoffs & What I'd Change

**What I Simplified for Speed:**

| Simplification | Production Version |
|----------------|-------------------|
| In-memory session storage (Python dict) | Redis or database-backed sessions with Time To Live (TTL) and expiry |
| Mock tool functions | Real API integrations with systems for orders, returns, etc. |
| No identity verification | Verify customer email or session token against order record before calling `get_order_status` |
| Prompt-only guardrails | Code-level validation for all operations with financial consequences |
| Single model, no fallback | Model routing with fallback (e.g., GPT-4o if Claude unavailable) |
| No rate limiting | Per-session rate limits to prevent abuse and order ID enumeration attacks |
| Print statement logging | Structured JSON logs to integrated with an observability platform |
| No conversation summarization | Summarize long histories to manage context window size and API cost |

**Highest Priority Production Change:**
Identity verification before any order data is surfaced. Currently any user
who knows an order ID can retrieve its details — a significant security gap.
In production, the agent would verify the customer's authenticated session
or email address against the order record before `get_order_status` is
permitted to execute. This is a code-level guardrail, not a prompt instruction,
because it must be enforced unconditionally.

**Second Priority Production Change:**
Replace prompt-level guardrails with code-level validation for all operations
with financial consequences. Prompts can be edge-cased under adversarial
inputs; tool-layer validation cannot. The return eligibility check in
`process_return_request` demonstrates this pattern — the same approach should
extend to refund limits, identity verification, and any action that touches
customer financial data.