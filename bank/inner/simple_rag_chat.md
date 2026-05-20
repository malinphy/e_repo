# Bank Chatbot — Starting Architecture

**Scope:** Informational only, web widget, authenticated user, greenfield.

Informational + authenticated user keeps it relatively lean — most complexity comes from retrieval quality and guardrails, not transactional safety.

## Request flow

```
[Web Widget]
     │  (JWT/session from main banking app)
     ▼
[API Gateway]  ── authn check, rate-limit, WAF
     │
     ▼
[Chat Orchestrator]  ── session store, turn state, routing
     │
     ├──► [Input Guardrails]  ── PII scrub, prompt-injection filter, topic gate
     │
     ├──► [Retriever]
     │       ├── Vector store (embeddings of FAQs, product docs, fees, T&Cs)
     │       └── BM25/keyword index  →  hybrid + rerank
     │
     ├──► [User Context Service]  ── segment, locale, products held (read-only)
     │
     ├──► [LLM]  ── system prompt + retrieved chunks + user context
     │
     ├──► [Output Guardrails]  ── hallucination check, compliance lint, citation enforcement
     │
     └──► [Audit Log]  ── every turn, immutable
     │
     ▼
[Widget renders answer + sources + feedback buttons]
     │
     └── "Talk to an agent" → [Live Agent Handoff]
```

## Component notes (the non-obvious bits)

- **Orchestrator** — keep it stateless; put session in Redis. Don't bake a heavy framework in early; a thin Python/Node service is fine.
- **Retrieval** — hybrid (vector + BM25) beats pure vector on banking content because product names, fee codes, and acronyms are exact-match heavy. Add a reranker (Cohere/cross-encoder) — biggest quality lever for the cost.
- **Knowledge base pipeline** — separate path: content team publishes → chunker → embedder → index. Version it; you'll need to roll back a bad doc.
- **User context** — even informational bots get huge wins from "your card X has Y benefit." Pass only the minimum into the prompt; never the full profile.
- **Guardrails** — at minimum: (a) refuse out-of-scope, (b) refuse advice-giving (investment, legal, tax), (c) require citations from retrieved docs, (d) PII redaction in logs.
- **Audit log** — regulators will ask. Store full prompt, retrieved chunks, response, model version, guardrail decisions. Immutable + retention policy.
- **Handoff** — even a basic "open ticket / route to live chat" button is critical for trust and for capturing failure cases.

## Decisions to make early (these shape everything)

1. **Hosted vs self-hosted LLM** — regulator stance on data leaving your perimeter often forces this. Affects vendor choice and latency budget.
2. **Single LLM call vs. agentic** — for informational, start with single-shot RAG. Don't add tool-calling loops yet.
3. **Languages** — Turkish + English? Embedding model and reranker choice depends on it.
4. **Eval harness from day one** — golden Q&A set (~200 questions), automated scoring on every prompt/index change. Without this you can't ship safely.

## What I'd defer

- Multi-turn clarification dialogs (start with single-turn + "rephrase")
- Personalized recommendations
- Voice
- Fine-tuning — exhaust prompting + retrieval first
