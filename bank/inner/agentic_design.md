# Agentic Bank Chatbot — System Design

## High-level architecture

```
┌─────────────────┐
│  Channels       │  Web widget / Mobile SDK / WhatsApp
│  (renders rich  │  — sends user msg + session token
│   UI elements)  │  — renders cards, buttons, forms from bot
└────────┬────────┘
         │ (HTTPS, WebSocket for streaming)
┌────────▼────────┐
│  BFF / Gateway  │  Auth (OIDC), rate limit, PII redaction in/out,
│                 │  audit log, request tracing
└────────┬────────┘
         │
┌────────▼────────────────────────────────────────────┐
│  Orchestrator (the agent loop)                       │
│  ┌──────────────┐   ┌───────────────┐   ┌────────┐  │
│  │ LLM (tool-   │◄─►│ Conversation  │   │ Policy │  │
│  │ calling)     │   │ state store   │   │ engine │  │
│  └──────┬───────┘   │ (Redis+PG)    │   │ (OPA)  │  │
│         │           └───────────────┘   └────────┘  │
│         │ tool_use                                   │
│  ┌──────▼─────────────────────────────────────────┐ │
│  │  Tool Registry  (schema + auth + risk tier)     │ │
│  └──┬──────────┬──────────┬──────────┬─────────────┘ │
└─────┼──────────┼──────────┼──────────┼──────────────┘
      │          │          │          │
   ┌──▼──┐   ┌──▼───┐   ┌──▼────┐  ┌──▼─────┐
   │Read │   │Write │   │ RAG   │  │Handoff │
   │APIs │   │APIs  │   │knowl. │  │to human│
   └─────┘   └──────┘   └───────┘  └────────┘
   balance   transfer   policies   live agent
   txns      card-freeze FAQs      ticketing
   profile   dispute     products
```

## Key design decisions specific to banking

**1. Tool risk tiering** — every tool gets a tier that determines what's required to call it:
- **T0 read-only** (balance, recent txns): session auth enough
- **T1 low-risk write** (card freeze, alert toggle, dispute open): session auth + explicit user confirmation in chat
- **T2 high-risk write** (transfer, bill pay, limit raise): step-up auth (OTP/biometric) + idempotency key + confirmation card showing exact params

The orchestrator doesn't decide this — a **policy engine** (e.g. OPA) sits between tool call and execution. Keeps policy out of the prompt where it can be jailbroken.

**2. Confirmation as a structured turn, not free text** — for any T1/T2 action, the agent emits a `confirmation_card` (amount, payee, account, fee) and the *user* clicks Confirm. The LLM never executes; the frontend posts a signed confirmation back. This is the single biggest safety win.

**3. Conversation state** — two layers:
- Short-term: Redis, full message history + tool results, TTL ~30min
- Long-term: Postgres, summarized memory per customer (preferences, recurring payees, recent disputes) — fed in as context, not retrieved by the LLM

**4. RAG stays, as a tool** — your existing RAG becomes one tool (`search_policy_docs`) the agent calls when it needs to ground an answer. Don't dump it into every prompt.

**5. Hallucination on numbers is the worst failure mode** — never let the LLM compute or restate numeric values. Tool returns the number; UI renders it from structured output, not from LLM prose. Validate that any number in the LLM's text appears verbatim in a tool result.

**6. Prompt injection defense** — assume any document, transaction memo, or payee name retrieved by a tool is hostile. Tool results go in as `tool_result` blocks, not concatenated into the system prompt. Strip/escape user-controlled fields before they reach the LLM.

## What I'd build first (MVP slice)

1. Orchestrator with 3 read-only tools: `get_balance`, `get_recent_transactions`, `search_faq` (your RAG)
2. One T1 write to prove the confirmation pattern: `freeze_card`
3. Conversation state in Redis, audit log to Postgres
4. Eval harness with ~50 scripted conversations covering happy path, ambiguous intent, prompt injection, and "agent should refuse"

This shape lets you validate the agent loop, tool-calling reliability, and the confirmation UX before touching money-movement tools.
