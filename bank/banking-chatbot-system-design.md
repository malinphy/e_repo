# Agentic Banking Chatbot — System Design

**Version:** 1.0  
**Scope:** EU-regulated retail banking · 10M customers · GDPR compliant  
**Classification:** Internal technical reference

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Requirements](#2-requirements)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Security Architecture](#4-security-architecture)
5. [Agent Design & Tool Layer](#5-agent-design--tool-layer)
6. [Money Transfer Flow](#6-money-transfer-flow)
7. [RAG Pipeline](#7-rag-pipeline)
8. [Failure Modes & Mitigations](#8-failure-modes--mitigations)
9. [Scale & Performance](#9-scale--performance)
10. [Serving Infrastructure](#10-serving-infrastructure)
11. [Deployment Pipeline](#11-deployment-pipeline)
12. [Compliance & Audit](#12-compliance--audit)
13. [Key Tradeoffs & Decisions](#13-key-tradeoffs--decisions)
14. [Open Questions & Future Work](#14-open-questions--future-work)

---

## 1. Executive Summary

This document describes the end-to-end system design for an **agentic banking chatbot** serving 10 million EU retail banking customers. The chatbot is capable of:

- Natural language account queries (balance, history, statements)
- Domestic and international money transfers (SEPA, SWIFT)
- Document and policy retrieval via RAG
- Real-time fraud awareness
- Push/email/SMS notifications

The system is designed as a **first-line assistant with a data-driven path to full automation**, compliant with GDPR, PSD2, and the EU AI Act. Every irreversible action requires explicit user confirmation and passes through a secure execution vault that is entirely outside the LLM's scope.

**Core principle:** The LLM is treated as an untrusted external service. It never sees raw PINs, full IBANs, SCA tokens, or unmasked account data.

---

## 2. Requirements

### 2.1 Functional Requirements

| Capability | Details |
|---|---|
| Account queries | Balance, transaction history, statements |
| Money transfers | Domestic (SEPA) and international (SWIFT) |
| Document retrieval | Policy PDFs, interest rates, product docs, contracts |
| Fraud awareness | Risk scoring on every transfer attempt |
| Notifications | Push, email, SMS for transaction events |
| Confirmation gate | Every irreversible action requires explicit user approval |

### 2.2 Non-Functional Requirements

| Dimension | Target |
|---|---|
| Users | 10M customers |
| DAU (5% active) | 500K |
| Peak load | ~100 msg/sec (3× daily average) |
| Response time | p50 < 1.5s · p99 < 3s (streamed) |
| Availability | 99.99% (~52 min downtime/year) |
| Jurisdiction | EU — GDPR, PSD2, EU AI Act |
| Channels | Web app (React SPA + WebSocket) |
| Audit retention | 7 years (regulatory minimum) |

### 2.3 Back-of-Envelope Numbers

```
10M customers × 5% DAU          = 500K daily active users
500K DAU × 3 messages/session   = 1.5M messages/day
1.5M / 12 active hours          = ~35 msg/sec average
3× spike multiplier             = ~100 msg/sec peak

Transfer volume (1% of sessions) = ~5,000 transfers/day
Average transfer latency target   = < 3s (SEPA) / async (SWIFT)
```

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLIENT LAYER                                           │
│  React SPA · WebSocket · TLS 1.3                        │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS / WSS
┌───────────────────────▼─────────────────────────────────┐
│  API GATEWAY (edge)                                     │
│  OAuth 2.0 + MFA · Rate limiting · Session management   │
└───────────────────────┬─────────────────────────────────┘
                        │ session_token only (no raw PII)
┌───────────────────────▼─────────────────────────────────┐
│  AGENT ORCHESTRATOR (LLM core)                          │
│  Intent classification · Tool selection · Planning      │
│  Conversation memory · Confirmation gating              │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │  tool calls
   ▼          ▼          ▼          ▼          ▼
Account    Transfer    RAG       Fraud     Notification
 Tool       Tool       Tool      Tool        Tool
   │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┘
                        │ API calls
┌───────────────────────▼─────────────────────────────────┐
│  CORE BANKING INTEGRATION LAYER                         │
│  REST / ISO 20022 · SEPA · SWIFT · Circuit breakers     │
└──┬──────────┬──────────┬──────────────────────────────┘
   ▼          ▼          ▼          ▼
Core DB   Vector DB   Redis    Document Store
Ledger    Embeddings  Session  S3 · PDFs
          (RAG)       Cache
                        │
┌───────────────────────▼─────────────────────────────────┐
│  AUDIT BUS (Kafka — async, cross-region replicated)     │
│  Every action · approval · tool call · GDPR lineage     │
└─────────────────────────────────────────────────────────┘
```

### 3.1 Layer Responsibilities

**API Gateway** is the security perimeter. It issues and validates session tokens, enforces rate limits, terminates TLS, and manages WebSocket connections. Nothing reaches the LLM without passing through here.

**Agent Orchestrator** is the LLM core. It receives masked, session-tagged context — never raw PII. Its job is intent classification, tool selection, multi-step planning, and enforcing the confirmation gate before any write action is executed.

**Tool Layer** is a set of five single-responsibility tools. Each tool calls downstream services and returns structured, masked results to the orchestrator. The Transfer tool and Account tool are the only tools with write access to core banking — and only via the Secure Vault.

**Core Banking Integration** is an adapter layer translating tool calls into ISO 20022 messages or REST. It owns circuit breakers, retry logic, and idempotency key management.

**Audit Bus** receives an asynchronous write from every component on every meaningful event. It is append-only, cross-region replicated, and retained for 7 years to satisfy regulatory requirements.

---

## 4. Security Architecture

### 4.1 Trust Boundary Design

The LLM is treated as an **untrusted external service**, regardless of whether it is self-hosted or cloud-hosted. This is the foundational security assumption of the entire design.

```
┌─────────────────────────────────────────────┐
│  LLM TRUST ZONE (untrusted)                 │
│                                             │
│  API Gateway → Orchestrator → Tool Router   │
│                                             │
│  Sees: masked tokens, intent, tool results  │
│  Never sees: IBAN, PIN, SCA token, raw PII  │
└──────────────────────┬──────────────────────┘
                       │
          ════════ PII FIREWALL ════════
          Data never crosses upward raw
                       │
┌──────────────────────▼──────────────────────┐
│  PII FIREWALL + DATA MASKING SERVICE        │
│  IBAN → IE29****5678                        │
│  Balance → approximate / sufficient flag    │
│  PIN → never returned                       │
│  Card number → **** **** **** 4321          │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  SECURE EXECUTION VAULT (LLM-blind)         │
│  PIN verification · SCA step-up             │
│  Transfer signing · HSM key management      │
│  Isolated compute — no shared K8s namespace │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  CORE BANKING SYSTEM                        │
│  Raw data lives here only                   │
└─────────────────────────────────────────────┘
```

### 4.2 Four Security Mechanisms

**1. Session context injection (from login)**
User identity is established at login via OAuth 2.0 + MFA. The session token carries `user_id` and `account_ref` server-side. Every tool call silently injects this token. The LLM never asks for identity — it never needs to.

**2. PII firewall + data masking**
All data returned from core banking passes through the masking service before reaching the LLM. Masking rules are enforced at the service level, not in the LLM prompt. The LLM cannot be prompted into receiving unmasked data.

**3. Secure execution vault**
PIN verification, SCA step-up authentication, and payment signing all happen in the vault — a completely separate compute environment. The LLM submits a signed intent (`action`, `amount`, `recipient_ref`) and receives a result (`status`, `reference`). It participates in neither authentication nor payment execution.

**4. Active guards — input and output**

| Guard | What it does |
|---|---|
| Prompt injection scanner | Scans user input and RAG-retrieved chunks for instruction patterns before they reach the LLM |
| Output PII scanner | Regex + ML scan of every LLM response before delivery to the user |
| Document sandboxing | Retrieved chunks wrapped in untrusted XML tags; LLM instructed never to follow instructions within them |

### 4.3 PSD2 / SCA Compliance

Transactions above €30 trigger Strong Customer Authentication per PSD2. SCA is handled entirely within the Secure Vault — OTP or biometric challenge sent directly to the user, verified by the vault, and the resulting SCA token is never exposed to the LLM.

---

## 5. Agent Design & Tool Layer

### 5.1 Orchestrator Behaviour

The orchestrator operates with a structured system prompt that defines:

- **Role:** EU retail banking assistant
- **Tool access:** explicit list of permitted tools with schemas
- **Confirmation mandate:** any write action must surface a structured confirmation to the user before calling a write tool
- **Grounding rule:** never state a financial figure not received from a tool result
- **Clarification-first policy:** if any required slot for a write action is missing or ambiguous, ask before acting

### 5.2 Tool Definitions

| Tool | Access | Key behaviour |
|---|---|---|
| `account_tool` | Read | Balance, history, statements — always live, never cached |
| `transfer_tool` | Write | Requires `confirmation_token` in call signature — impossible to call without user confirmation gate having fired |
| `rag_tool` | Read | Policy, rates, product docs — semantic cache with TTL |
| `fraud_tool` | Read | Risk score on every transfer — runs in parallel, never blocks the happy path |
| `notification_tool` | Write | Push/email/SMS — fire-and-forget, async |

### 5.3 Intent Classification (Pre-LLM)

A lightweight classifier runs before the main LLM on every message. It labels intent as:

- `read` → route to small/mid model
- `write` → route to large model, enforce slot-filling
- `ambiguous` → request clarification before any routing

This classifier runs in under 50ms and prevents the main LLM from ever misrouting a read/write intent at the tool-selection level.

### 5.4 Slot-Filling for Transfers

Before the transfer tool can be called, four slots must be filled:

```
recipient  — resolved from saved payees, not free text
amount     — explicit, confirmed by user
account    — source account (from session context)
timing     — immediate or scheduled
```

If any slot is empty, the LLM must ask specifically for that slot. No assumptions are ever made on irreversible actions.

---

## 6. Money Transfer Flow

The following is the exact sequence for `"Transfer €5,000 to John"`:

```
① User message arrives → API Gateway validates session token
② Intent classified as write:transfer
③ Orchestrator resolves "John" → Vault looks up saved payees
   → Returns: "John Smith · IE29****5678" (masked)
   → If multiple Johns: LLM asks user to disambiguate
④ All 4 slots confirmed (recipient, amount, account, timing)
⑤ Orchestrator generates structured confirmation:
   {action: confirm_transfer, to: "John Smith",
    masked_iban: "IE29****5678", amount: 5000, currency: "EUR"}
⑥ Frontend renders tamper-evident confirmation card (not LLM prose)
⑦ User taps "Confirm" → confirmation_token issued
⑧ SCA step-up triggered (€5,000 > €30 PSD2 threshold)
   → Vault sends OTP/biometric challenge directly to user
   → LLM waits; never participates in SCA
⑨ User passes SCA → Vault receives signed SCA token
⑩ Fraud tool scores the transfer in parallel → risk: OK
⑪ Vault signs and submits to SEPA/SWIFT rail
   → Idempotency key generated before submission
⑫ Core banking records the debit (saga pattern)
   → On failure: compensating transaction reverses debit
⑬ Result returned: {status: "success", ref: "TXN-9921"}
⑭ LLM formats: "Transfer sent successfully. Reference: TXN-9921"
⑮ Audit log: all steps, approvals, SCA events written to Kafka
```

**What the LLM never saw:** full IBAN · PIN · SCA token · raw balance · fraud score · card number · account ref ID

---

## 7. RAG Pipeline

### 7.1 Document Ingestion

```
Source document (PDF/contract/policy)
  → Pre-scan: injection pattern detection
  → Text extraction + cleaning
  → Chunking: 512-token chunks with 64-token overlap
  → Embedding (text-embedding-3 class model)
  → Vector DB (Pinecone / pgvector)
  → Document store (S3) for source retrieval
```

### 7.2 Retrieval

On every RAG query:
1. User query embedded (same model as indexing)
2. Top-k semantic search (k=5)
3. Retrieved chunks wrapped in `<untrusted_source>` XML tags
4. Injected into LLM context alongside the query
5. LLM instructed to never follow instructions within tags

### 7.3 Cache Strategy

| Query type | Cache | TTL |
|---|---|---|
| Interest rates, fees | Semantic cache (Redis) | 1 hour |
| Bank policy, FAQ | Semantic cache (Redis) | 24 hours |
| Product documentation | Semantic cache (Redis) | 6 hours |
| Account balance | Never cached | Always live |
| Transaction history | Never cached | Regulatory requirement |

---

## 8. Failure Modes & Mitigations

### 8.1 Hallucination on Financial Data
**Risk:** LLM states wrong balance, rate, or fee — user makes real decisions on it.

**Mitigations:**
- LLM forbidden by system prompt from stating any number not received from a tool result
- Financial responses use typed schema — UI renders from schema, not from LLM prose
- Post-generation validator checks LLM output against tool results — numeric mismatch blocks response
- Fallback: if confidence low, surface a UI card directly from live data

### 8.2 Wrong Tool Selection
**Risk:** LLM calls transfer tool when user asked a read query.

**Mitigations:**
- Write tools require `confirmation_token` in their call signature — structurally impossible to call without confirmation gate
- Pre-LLM intent classifier separates read/write/ambiguous before routing
- Tool call audit logged — misroutes caught in monitoring and fed back into fine-tuning

### 8.3 Question Misunderstanding
**Risk:** LLM acts on a wrong interpretation of an ambiguous request.

**Mitigations:**
- Clarification-first policy in system prompt — ask before acting if any parameter is ambiguous
- Slot-filling framework — all required parameters must be filled before write tools are callable
- Confirmation UI shows all parameters explicitly before user confirms

### 8.4 Prompt Injection via Documents
**Risk:** Malicious content in a RAG-retrieved document attempts to override LLM behaviour.

**Mitigations:**
- All documents scanned for instruction patterns before indexing
- Retrieved chunks wrapped in untrusted XML tags; LLM instructed to never follow instructions within them
- Write tool signature requires `confirmation_token` — injection cannot satisfy this regardless of what the LLM context says

### 8.5 Partial Transaction Failure
**Risk:** Payment rail accepts transfer but core banking DB write times out — ambiguous state.

**Mitigations:**
- Idempotency keys generated before every transfer submission — retries are safe
- Saga pattern — debit and credit staged separately with compensating transactions on failure
- Ambiguous state response: "your transfer is being processed — check your transaction history in a few minutes" — never "failed" or "succeeded" until confirmed

### 8.6 LLM Provider Outage
**Risk:** Primary LLM provider goes down — full chatbot unavailability.

**Mitigations:**
- Circuit breaker: if p95 latency > 5s or error rate > 1%, automatically switch to fallback provider
- Fallback LLM: different cloud provider, same masked context contract
- Degraded mode: small self-hosted model handles read queries; write actions queued for recovery

---

## 9. Scale & Performance

### 9.1 Model Routing — The Key Optimisation

Not all queries need the same model. Routing by complexity reduces cost by ~65% and cuts p50 latency significantly.

| Tier | Model size | Latency | Traffic share | Query types |
|---|---|---|---|---|
| Fast | Small (7B class) | < 500ms | ~60% | FAQ, rates, policy, simple balance |
| Mid | Mid (30B class) | 1–2s | ~35% | Account analysis, history, comparison |
| Slow | Large (frontier) | 3–5s streamed | ~5% | Multi-step transfers, disputes, doc reasoning |

The pre-LLM intent classifier makes the routing decision in < 50ms.

### 9.2 Latency Strategy

**Streaming:** First token delivered in < 800ms. User perceives fast response even when generation takes 3s. For tool calls, the orchestrator streams thinking-phase text while the tool call executes in parallel.

**Async task queue:** Anything > 500ms (SWIFT transfers, document processing, fraud scoring) returns immediately with a job ID. Result pushed over WebSocket when ready. Users never wait synchronously for payment rails.

**Caching:** Static knowledge cached aggressively (semantic cache, TTL-based). Account state never cached — always live from core banking.

### 9.3 Autoscaling

Orchestration pods are stateless — all session state in Redis. Kubernetes HPA watches CPU and request queue depth. New pods spin up in < 60 seconds. No warm-up complexity because there is no local state to initialise.

---

## 10. Serving Infrastructure

### 10.1 Multi-Region Active-Active

```
Global Load Balancer (GeoDNS · anycast · failover < 30s)
         │                              │
         ▼                              ▼
   eu-west-1 (primary)           eu-north-1 (failover)
   ─────────────────             ─────────────────────
   API Gateway cluster           API Gateway cluster
   Orchestrator pods (K8s HPA)   Orchestrator pods (warm standby)
   Tool worker pool              Tool worker pool
   Redis cluster                 Redis replica (async sync)
   Vector DB                     Vector DB (read replica)
   Secure Vault (isolated)       Secure Vault (independent HSM)
   Core banking adapter          Core banking adapter
```

Async replication of session state and vector DB between regions. The Secure Vault in each region has its own independent HSM — no shared cryptographic state across regions.

### 10.2 LLM Provider Redundancy

```
Primary LLM provider  ──(circuit breaker)──▶  Fallback LLM provider
                                                        │
                                              (both fail)
                                                        │
                                                        ▼
                                            Self-hosted small model
                                            (read-only degraded mode)
```

99.99% uptime cannot be achieved with a single LLM provider. Provider redundancy is non-negotiable.

### 10.3 Data Layer

| Store | Technology | Purpose | Cache policy |
|---|---|---|---|
| Core banking DB | PostgreSQL (managed) | Ledger, accounts, transactions | Never cached |
| Vector DB | Pinecone / pgvector | RAG embeddings | Read replica in failover |
| Session cache | Redis Cluster | Conversation state, semantic cache | TTL per query type |
| Document store | S3 + CDN | PDFs, contracts, policy docs | CDN-cached, TTL 24h |
| Audit log | Kafka (cross-region) | Immutable event log | Retained 7 years |

---

## 11. Deployment Pipeline

### 11.1 Pipeline Stages

```
Code commit (Git · PR review · branch protection)
        │
        ▼
CI pipeline (unit · integration · SAST · secret scan)
        │
        ▼
LLM eval suite (500 golden prompts · hallucination bench · injection attempts)
        │
        ▼
Container build (Docker · image signing · registry push)
        │
        ▼
Staging (full-stack · synthetic data · pen-test · load test · E2E)
        │
        ▼  [Security approval gate — required]
        │
        ▼
Canary deploy (5% real traffic · 30-minute soak)
  Monitor: p99 latency · error rate · LLM accuracy
  Auto-rollback if thresholds breached
        │
        ▼  [Canary gate: p99 < 3s · error < 0.1% · accuracy > 98%]
        │
        ▼
Progressive rollout: 5% → 25% → 50% → 100%
  15-minute soak at each step · auto-advance on healthy metrics
        │
        ▼
Production (both regions · HPA active · audit logging)
```

### 11.2 LLM Eval Suite — Deploy Gate

Every deploy must pass the LLM eval suite before reaching staging. A failing eval blocks the deploy automatically.

| Metric | Threshold | Action on breach |
|---|---|---|
| Hallucination rate | > 2% | Block deploy |
| Tool misroute rate | > 1% | Block deploy |
| PII leakage | Any detection | Block deploy |
| Adversarial prompt pass-through | Any detection | Block deploy |
| Latency regression vs baseline p99 | > 15% | Block deploy |

### 11.3 Banking-Specific Deployment Rules

**Prompt versioning:** System prompts are stored in Git alongside code. Every prompt change is a tagged, signed release — not a config file edit. Prompt changes go through the full pipeline, including the LLM eval suite.

**Zero-downtime deploys:** Rolling updates with readiness probes. A pod is not added to the load balancer until it has passed its readiness check. No active sessions are dropped during a deploy.

**Feature flags:** New agent tools are dark-launched — deployed but disabled. They are enabled progressively per user cohort (e.g., 1% of users → 10% → 100%), with a kill switch available at all times.

---

## 12. Compliance & Audit

### 12.1 GDPR

| Requirement | Implementation |
|---|---|
| Data minimisation | LLM receives only masked tokens and tool results |
| Data processor agreement | DPA signed with all LLM providers (Art. 28) |
| Right to erasure | Conversation logs pseudonymised — user_id deletable independently of audit events |
| Data residency | All data stored in EU regions (eu-west-1, eu-north-1) |
| Consent | Chatbot onboarding captures explicit consent for AI processing |

### 12.2 PSD2

| Requirement | Implementation |
|---|---|
| Strong Customer Authentication | SCA step-up in Secure Vault for transactions > €30 |
| Dynamic linking | Transfer confirmation card links SCA challenge to specific amount and recipient |
| Transaction monitoring | Fraud tool runs on every transfer — score logged to audit bus |

### 12.3 EU AI Act

The banking chatbot is classified as **high-risk AI** under EU AI Act Annex III (critical infrastructure — financial services). This requires:

- Human oversight mechanisms → escalation path to human agents retained
- Audit trail of AI decisions → Kafka audit bus, 7-year retention
- Accuracy and robustness testing → LLM eval suite on every deploy
- Transparency to users → chatbot discloses it is an AI at session start

### 12.4 Audit Log Schema

Every event written to Kafka contains:

```json
{
  "event_id": "uuid",
  "timestamp": "ISO8601",
  "session_id": "uuid",
  "user_ref": "pseudonymised_id",
  "event_type": "tool_call | user_confirmation | sca_event | transfer_submitted",
  "tool": "transfer_tool | account_tool | ...",
  "input_masked": { "intent": "transfer", "amount": 5000 },
  "output_masked": { "status": "success", "ref": "TXN-9921" },
  "llm_model": "model_id + version",
  "region": "eu-west-1",
  "immutable": true
}
```

---

## 13. Key Tradeoffs & Decisions

### 13.1 Cloud LLM vs Self-Hosted

**Decision: Cloud first, with a defined migration path.**

Cloud LLM is the correct starting point. The PII firewall ensures raw customer data never leaves the bank's perimeter — only masked tokens are sent to the LLM provider. The DPA under GDPR Art. 28 provides the legal framework.

The migration path: after 12 months of production traffic data, fine-tune a smaller self-hosted model on anonymised query logs. Move FAQ and account queries to self-hosted. Keep complex reasoning (transfers, disputes) on cloud. This is the industry-standard playbook.

### 13.2 Latency vs Accuracy

**Decision: Route validation by response type, not blanket apply or blanket skip.**

The post-generation validator (800ms overhead) is mandatory for any response containing financial figures or action confirmations. It is skipped for policy/FAQ responses routed to the small model tier. This gives < 500ms for the majority of traffic and full accuracy guarantees where it matters.

### 13.3 Full Replacement vs First-Line Assistant

**Decision: Launch as first-line assistant. Earn full automation with data.**

Full replacement at launch carries unacceptable regulatory and reputational risk (EU AI Act requires human oversight; one bad transfer has outsized consequences). The correct approach:

1. Launch with escalation path to human agents
2. Measure: resolution rate, escalation rate, CSAT, error rate per query type
3. After 90 days: if chatbot handles > 80% of queries at > 95% accuracy, disable escalation for those query types
4. Full automation is earned through evidence, not assumed

---

## 14. Open Questions & Future Work

| Topic | Question | Priority |
|---|---|---|
| Voice channel | Extend to voice banking — additional latency constraints, ASR pipeline needed | Medium |
| Multi-language | EU banking requires support for local languages — evaluate multilingual model vs translation layer | Medium |
| Fine-tuning | At what traffic volume does fine-tuning a domain-specific model justify the infra cost? | High |
| Personalisation | Should the chatbot learn user preferences over time? Privacy implications under GDPR. | Medium |
| Agentic escalation | When the chatbot escalates, how does it hand off full context to a human agent cleanly? | High |
| Regulatory changes | Monitor EU AI Act implementing acts for banking-specific guidance (expected 2025–2026) | High |

---

*Document generated from system design interview session. All architecture decisions include rationale and tradeoff analysis. For implementation questions, contact the platform engineering team.*
