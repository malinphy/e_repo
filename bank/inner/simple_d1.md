# Bank Chatbot — Architecture Diagram

Companion to [simple_rag_chat.md](simple_rag_chat.md).

## Mermaid

```mermaid
flowchart TD
    U[User] --> W[Web Widget]
    W -->|JWT / session| GW[API Gateway<br/>authn · rate-limit · WAF]
    GW --> ORCH[Chat Orchestrator<br/>session · routing]

    ORCH --> IG[Input Guardrails<br/>PII scrub · injection filter · topic gate]
    IG --> RET[Retriever]

    subgraph KB [Knowledge Base]
        VS[(Vector Store)]
        BM[(BM25 Index)]
    end

    RET --> VS
    RET --> BM
    RET --> RR[Reranker]

    ORCH --> UCTX[User Context Service<br/>segment · locale · products]

    RR --> LLM[LLM]
    UCTX --> LLM
    LLM --> OG[Output Guardrails<br/>hallucination · compliance · citations]

    OG --> ORCH
    ORCH --> AUD[(Audit Log<br/>immutable)]
    ORCH --> W
    W -->|escalate| HA[Live Agent Handoff]

    subgraph CONTENT [Content Pipeline]
        DOCS[Source Docs] --> CHUNK[Chunker] --> EMB[Embedder] --> VS
        DOCS --> BM
    end
```

## ASCII fallback

```
                  ┌──────────────┐
                  │     User     │
                  └──────┬───────┘
                         ▼
                  ┌──────────────┐
                  │  Web Widget  │
                  └──────┬───────┘
                         │ JWT
                         ▼
                  ┌──────────────┐
                  │ API Gateway  │  authn · rate-limit · WAF
                  └──────┬───────┘
                         ▼
                  ┌──────────────────┐
                  │  Orchestrator    │◄────────┐
                  └──┬────────────┬──┘         │
                     │            │            │
                     ▼            ▼            │
            ┌────────────┐  ┌──────────────┐   │
            │  Input GR  │  │ User Context │   │
            └─────┬──────┘  └──────┬───────┘   │
                  ▼                │           │
            ┌────────────┐         │           │
            │  Retriever │         │           │
            │  ┌──────┐  │         │           │
            │  │Vector│  │         │           │
            │  │ BM25 │  │         │           │
            │  │Rerank│  │         │           │
            │  └──────┘  │         │           │
            └─────┬──────┘         │           │
                  └─────┬──────────┘           │
                        ▼                      │
                  ┌──────────┐                 │
                  │   LLM    │                 │
                  └────┬─────┘                 │
                       ▼                       │
                  ┌──────────┐                 │
                  │ Output GR│─────────────────┘
                  └────┬─────┘
                       ▼
                  ┌──────────┐    ┌──────────────┐
                  │Audit Log │    │ Live Agent   │
                  └──────────┘    │  Handoff     │
                                  └──────────────┘
```

## Legend

| Element        | Purpose                                                |
|----------------|--------------------------------------------------------|
| Input GR       | PII scrubbing, prompt-injection filtering, topic gate  |
| Output GR      | Hallucination check, compliance lint, citation check   |
| Reranker       | Cross-encoder reorder of hybrid retrieval results      |
| User Context   | Read-only: segment, locale, products held              |
| Audit Log      | Immutable per-turn record for regulator review         |
