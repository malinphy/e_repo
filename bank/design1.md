# Banking Chatbot — System Design

## Constraints & Scope

| Parameter | Decision |
|-----------|----------|
| Scale | Worldwide bank |
| Queries | Read-only: account queries + knowledge base |
| Channel | Web chat, embedded in existing banking app |
| Region | EU single region (GDPR + PSD2) |
| Auth | Users already authenticated (JWT) |
| LLM | Azure OpenAI — Sweden Central (primary), France Central (failover) |

---

## High-Level Architecture

```
[Banking Web App]
      | JWT
      v
[API Gateway]  →  [WAF / DDoS Protection]
      |
      v
[Orchestration Service]  ←→  [Redis - Session State (TTL 30min)]
   Azure VNet
    /        \
   v          v
[pgvector]  [Core Banking API]
(RAG store)  (read-only, internal)
   \          /
    v        v
  [LLM Abstraction Layer]
         |
    Private Endpoint
         |
  [Azure OpenAI - Sweden Central]  (PTU - primary)
         |  (failover)
  [Azure OpenAI - France Central]  (Standard tier)
```

---

## Query Types

| Type | Example | Data Source |
|------|---------|-------------|
| Structured | "What's my balance?" | Core Banking API |
| Unstructured | "How do I dispute a charge?" | Knowledge Base (RAG) |

---

## Component Design

### Auth & Identity
- User's JWT flows with every chat request
- Chat Gateway validates JWT, extracts `user_id`
- All downstream calls use that identity
- Chatbot inherits session trust — never re-authenticates

### Orchestration Service
- Stateless, horizontally scalable
- Classifies intent → extracts entities → fills slots → fetches context → builds LLM prompt → returns response
- Conversation history in Redis keyed by `session_id` (TTL 30min)
- Tracks dialogue state (current intent, filled/missing slots) per session

### RAG Pipeline
- Bank docs (PDFs, FAQs, product pages) chunked at 512 tokens, 50-token overlap
- Embedded via Azure OpenAI `text-embedding-3-large`
- Stored in **pgvector on PostgreSQL** (EU-region, no extra managed service)
- Query path: embed user message → cosine similarity → top-K chunks → LLM context
- Same model version used at ingestion and query time (critical for vector compatibility)
- Azure OpenAI deployment version pinned to prevent silent model drift

### NER + Slot Filling + Entity Resolution

This layer bridges free-text user input and structured API calls.

#### Full Flow
```
[User Message]
      ↓
[Intent Classifier]
      ↓
[NER Layer]  →  Regex → NER Model → GPT-4o fn calling (fallback)
      ↓
[Slot Filler]  →  All slots filled? No → clarification turn
      ↓                               Yes → continue
[Entity Resolver]  →  Ownership check against Core Banking
      ↓
[Core Banking API / RAG]
      ↓
[PII Masker]
      ↓
[LLM — format only, never invent data]
      ↓
[Output Guardrails]  →  [Response]
```

#### NER Strategy — Three Layers

| Layer | Handles | Why |
|-------|---------|-----|
| **Regex rules** | IBANs, card numbers, dates, amounts | Known formats, fast, no model needed |
| **Small NER model** | Fuzzy refs: "my savings account", "the account I opened in January" | Lightweight spaCy/BERT, runs locally, no LLM cost |
| **GPT-4o function calling** | Complex ambiguous cases only | Fallback — more expensive, higher latency |

#### Slot Filling — Clarification on Missing Entities
```
User: "What's my balance?"   ← no account specified

[Slot Filler] → account_id: MISSING
Bot: "Which account would you like to check?
      • Checking account ending 1234
      • Savings account ending 5678"

User: "the savings one"
[NER] → resolves "savings one" → account_id: ACC_789
[Core Banking API call]
```

Session tracks slot state in Redis:
```json
{
  "current_intent": "balance_query",
  "slots": { "account_id": null },
  "awaiting_slot": "account_id"
}
```

#### Entity Resolution — Security Critical
After NER extraction, verify ownership before any API call:
```
Extracted IBAN:  ES91 2100 0418 4502 0005 1332
Authenticated:   user_id_456

GET /users/user_id_456/accounts
→ [ACC_789 (ES91...1332), ACC_790 (ES91...4421)]
→ ES91...1332 found ✓ → proceed with account_id: ACC_789
→ not found → reject + log security event (horizontal privilege escalation attempt)
```
LLM is never involved in this check — it is purely server-side logic.

---

### Core Banking API Client
- Read-only: balance, transactions, account details
- Server-side only — client never calls core banking directly
- Orchestration service attaches user identity claim

### PII Filter (pre-LLM)
Even with Azure OpenAI + DPA + private endpoints — PII is masked before sending:
- Account numbers → `****1234`
- Names → tokenized
- IBAN, card numbers → stripped

**Flow:**
```
User:        "What's my balance on account ES91 2100 0418 4502 0005 1332?"
Pre-LLM:     "What's my balance on account [IBAN_REDACTED]?"
Orchestrator fetches balance → injects structured context
LLM sees:    "Account ending 1332: €4,821.50"
Response:    "Your account ending in 1332 has a balance of €4,821.50"
```

### Guardrails Layer
- **Input**: Prompt injection detection, scope enforcement (refuse non-banking topics)
- **Output**: Confidence threshold — low confidence triggers human escalation
- **Hard rules**: No financial advice, no confirmation of fund movements

### Audit Logger
- Logs: `user_id` (hashed), `session_id`, timestamp, intent, data sources accessed
- Does NOT log raw conversation (GDPR data minimization)
- Append-only storage, retained per PSD2 (5 years)

---

## Azure OpenAI Integration

### Region & Network
- **Primary**: Sweden Central (PTU)
- **Failover**: France Central (Standard tier)
- Connected via **Azure Private Endpoint** — traffic never traverses public internet
- Orchestration service inside same Azure VNet

### Model Selection
| Purpose | Model |
|---------|-------|
| Chat | GPT-4o |
| Embeddings | text-embedding-3-large |

### Capacity
- **PTU (Provisioned Throughput Units)** for predictable latency
- Standard tier as overflow burst
- Estimated: ~50k DAU × 5 messages × 800 tokens = ~200M tokens/day baseline

### Authentication
- **Managed Identity** — no API keys
- Role: `Cognitive Services OpenAI User` on Azure OpenAI resource
- Full Azure RBAC audit trail

### GDPR Settings
- Abuse monitoring **disabled** (opt-out via Azure support) — banking data must not appear in Microsoft safety logs
- PII masking applied regardless (defense in depth)
- Microsoft DPA (Article 28) signed

### Failover
```
Circuit breaker triggers if:
  - Sweden Central P95 latency > 3s
  - Error rate > 1%
→ Auto-route to France Central
```

---

## Non-Functional Requirements

| Concern | Approach |
|---------|----------|
| Latency | Target <2s P95. Streaming responses to mask LLM latency |
| GDPR | No PII to LLM, right-to-erasure via session purge, DPA with Azure |
| Availability | 99.9% — circuit breaker on LLM, rule-based fallback for common queries |
| Scalability | Orchestration service horizontally scalable; Redis cluster for session state |
| Security | TLS everywhere, Private Endpoint, Managed Identity, PII masking |
| Compliance | PSD2 audit logs (5yr retention), GDPR data minimization |

---

## RAG Pipeline — Detail

### Ingestion
```
[Source Docs]  →  [Chunker]  →  [Embedder]  →  [pgvector]
 PDFs, FAQs,       semantic       Azure OAI
 Product pages     512 tok max    text-embed-3-large
                   50 tok overlap
```
- **Semantic chunking**: split on section headers/paragraph boundaries first, then enforce max token limit
- **Metadata per chunk**: `doc_id`, `section`, `language`, `last_updated`, `jurisdiction`
- Jurisdiction metadata enables pre-filtering: EU users only search EU-jurisdiction chunks

### Retrieval — Hybrid Search
```
Query: "What is the fee for SEPA instant transfers?"

Vector search  → semantic similarity → top-5 chunks
BM25 search    → keyword match "SEPA instant" → top-5 chunks
               ↓
         Re-ranker (cross-encoder, runs locally)
               ↓
         Top-3 final chunks → LLM context
```

### Context Window Budget
```
System prompt:          ~500 tokens
Conversation history:   ~1,000 tokens (last 4 turns)
Retrieved chunks:       ~1,500 tokens (top-3 × 500)
Account data injected:  ~200 tokens
User message:           ~100 tokens
─────────────────────────────────────
Total input:            ~3,300 tokens
Reserved for output:    ~500 tokens
```

---

## Session & Context Management

### Redis Session Schema
```json
{
  "session_id": "sess_abc123",
  "user_id": "hashed_uid",
  "turns": [
    {"role": "user", "content": "...", "ts": 1234567890},
    {"role": "assistant", "content": "...", "ts": 1234567891}
  ],
  "intent_history": ["balance_query", "kb_lookup"],
  "current_intent": "balance_query",
  "slots": { "account_id": null },
  "awaiting_slot": "account_id",
  "last_active": 1234567891
}
```

- Last **4 turns** kept in full; older turns summarized into a `summary` field via lightweight LLM call
- 30-minute sliding TTL — on expiry session purged (GDPR data minimization)

---

## Safety & Guardrails

### Input Guardrails
| Threat | Mitigation |
|--------|------------|
| Prompt injection | System prompt framing + input classifier |
| Jailbreak | Azure OpenAI built-in content filter |
| Scope creep | Intent classifier rejects non-banking queries before LLM call |
| Privilege escalation | Entity resolver verifies account ownership server-side |

### Output Guardrails
- **Hallucination fence**: account data always from Core Banking API — LLM formats, never invents numbers
- **Confidence threshold**: retrieval score < 0.7 → escalate to human agent
- **Disclaimer injection**: answers touching fees/rates/legal get hardcoded footer

### Human Escalation Triggers
```
if (confidence < 0.7) OR
   (user_sentiment == "angry") OR
   (topic == "fraud" OR "complaint") OR
   (3+ consecutive fallback responses):
     → route to live agent queue
     → pass full session context to agent
```

---

## Multi-Language Support

### Strategy: Native Multilingual + Hybrid RAG
- GPT-4o handles user's language natively — no translation step
- `text-embedding-3-large` is multilingual — cross-lingual retrieval works for general content
- Regulatory/legal content maintained in official translated versions (not LLM-translated)

### Language Detection
- **Azure Cognitive Services Language Detection** — first step in pipeline, before intent classification
- Result stored in Redis session
- Fallback: user's banking app locale setting if detection confidence < 0.8

### Dual-Track Knowledge Base
```
[Knowledge Base]
    ├── general/          ← FAQs, how-to guides — EN only, cross-lingual retrieval
    └── regulatory/       ← Fees, T&Cs, legal disclosures — official translations per language
          ├── en/
          ├── de/
          ├── fr/
          ├── es/
          ├── it/
          ├── nl/
          ├── pl/
          └── pt/
```
Regulatory chunks filtered by `language` metadata at retrieval time — never served cross-lingual.

### NER Across Languages
- IBANs, amounts, card numbers → regex (language-agnostic)
- Dates → multilingual date parser (Azure Cognitive Services)
- Fuzzy account references ("mon compte courant", "mein Sparkonto") → GPT-4o function calling with enum output

### Response Generation
System prompt: `"Always respond in {detected_language}. Use formal register appropriate for banking."`

**Legal disclaimers — never LLM-generated, always pre-translated strings:**
```python
DISCLAIMERS = {
    "en": "For binding information, refer to your account agreement.",
    "de": "Verbindliche Informationen finden Sie in Ihrem Kontovertrag.",
    "fr": "Pour des informations contraignantes, consultez votre contrat de compte.",
    ...
}
response = llm_response + "\n\n" + DISCLAIMERS.get(detected_lang, DISCLAIMERS["en"])
```

### EU Minimum Language Coverage
| Language | Coverage |
|----------|----------|
| EN | Base — all docs |
| DE | Germany, Austria |
| FR | France, Belgium |
| ES | Spain |
| IT | Italy |
| NL | Netherlands, Belgium |
| PL | Poland |
| PT | Portugal |

---

## Scalability at Extreme Load

### Load Estimation
```
Worldwide bank:     ~50M customers
Peak concurrent:    2% = 1M sessions
Messages/sec:       ~33,000 req/sec at peak

Each request:
  1 LLM call         (~1,000ms — primary bottleneck)
  1 RAG retrieval    (~100ms)
  1 Core Banking call (~50ms)
  1 Redis op          (~5ms)
```

### Strategy 1 — Smart Routing (Eliminate LLM Calls)
60-70% of banking queries are simple structured lookups — handle with templates, no LLM:

| Query | Strategy |
|-------|----------|
| "What's my balance?" | Core Banking API → fill template |
| "Last 5 transactions?" | Core Banking API → fill template |
| "What's my account number?" | Core Banking API → fill template |
| "How do I dispute a charge?" | RAG + LLM (complex) |

### Strategy 2 — Multi-Level Caching

| Cache Level | What | TTL |
|-------------|------|-----|
| **Semantic cache** (Redis) | RAG KB answers — matched by embedding similarity > 0.92 | 1 hour |
| **Account data cache** (Redis) | Core Banking responses | 30 seconds |
| **RAG chunk cache** (Redis) | Frequently retrieved chunks | 15 minutes |

Semantic cache hit rate for KB queries: ~40-60% (same questions, different phrasing).

### Strategy 3 — Queue-Based Architecture with KEDA
```
[API Gateway]
      ↓
[Azure Service Bus]        ← partitioned by user_id
      ↓
[Orchestration Workers]    ← K8s + KEDA, scales on queue depth
      ↓
[SSE Streaming response]   ← first token ~200ms, masks full latency
```

KEDA scales workers within seconds based on queue depth — not CPU lag.
Backpressure: queue > threshold → HTTP 429 with `Retry-After`.

**Request priority in queue:**
```
Priority 1: Active session mid-conversation
Priority 2: New session first message
Priority 3: Retry attempts
```

### Strategy 4 — Azure OpenAI Scaling
- PTU pool covers P75 load — Standard tier absorbs spikes
- Multiple PTU deployments spread token budget
- Streaming non-negotiable: perceived latency << actual latency
- After caching + smart routing: ~20% of raw requests reach LLM

### Strategy 5 — Database Scaling

**pgvector:**
- Primary for writes (ingestion pipeline)
- 3× read replicas for query traffic
- PgBouncer connection pool (pgvector can't handle 33k direct connections)

**Redis Cluster:**
- 6-node (3 primary + 3 replica), partitioned by `session_id`
- Session store: `allkeys-lru` eviction
- Semantic cache: separate cluster, `volatile-lru` eviction

### Strategy 6 — Rate Limiting
```
Per user:    20 messages/minute  (warn at 15)
Per session: 100 messages total
Global:      circuit breaker if error rate > 5% → graceful load shedding
```
Enforced at Azure API Management — before any compute is touched.

### Scaled Architecture
```
[50M Users — Banking Web App]
        ↓
[Azure Front Door + WAF]        ← global entry, DDoS protection
        ↓
[Azure API Management]          ← rate limiting, JWT validation
        ↓
[Azure Service Bus]             ← queue, partitioned by user_id
        ↓
[Orchestration Workers — KEDA]
    ↙              ↘
Simple queries    Complex queries
(template)        (RAG + LLM)
    ↓                  ↓
[Redis L2 cache]  [Redis L1 semantic cache]
    ↓                  ↓
[Core Banking]    [Azure OpenAI PTU + burst]
        ↓
[SSE Streaming → User]
```

### Load Reduction Summary
| Strategy | Impact |
|----------|--------|
| Smart routing (templates) | ~65% fewer LLM calls |
| Semantic cache | ~40% of remaining LLM calls served from cache |
| Account data cache | ~80% fewer Core Banking API calls |
| **Net LLM calls at peak** | **~20% of raw 33k req/sec = ~6,600 LLM req/sec** |

---

## Monitoring & Observability

### Four Metric Layers
```
Layer 1: Infrastructure   ← is the system up?
Layer 2: AI Quality       ← is the AI performing well?
Layer 3: Business/Product ← is the chatbot actually helping users?
Layer 4: Security         ← is anyone abusing it?
```

---

### Layer 1 — Infrastructure Metrics

| Component | Metric | Alert Threshold |
|-----------|--------|-----------------|
| API Gateway | Latency P95, error rate | P95 > 200ms, errors > 1% |
| Service Bus | Queue depth, oldest message age | depth > 10k, age > 30s |
| Orchestration | Latency P95, OOM kills | P95 > 500ms |
| Redis | Memory usage, eviction rate, hit rate | memory > 80%, evictions > 100/min |
| pgvector | Query latency, connection pool saturation | query > 200ms, pool > 90% |
| Azure OpenAI | Latency P95, throttle rate, PTU utilization | P95 > 3s, throttle > 0.5% |

**Golden Signals per service:** Latency (P50/P95/P99), Traffic (req/sec), Errors (4xx vs 5xx), Saturation (queue depth, memory, pool)

---

### Layer 2 — AI Quality Metrics

#### LLM Metrics
| Metric | What it tells you |
|--------|-------------------|
| Time to first token | Perceived latency — user experience |
| Total completion time | True LLM latency |
| Input/output token count | Cost tracking + prompt bloat detection |
| PTU utilization % | Capacity planning |
| Throttle rate | PTU exhausted, spilling to Standard tier |
| LLM error rate | Timeouts, content filter blocks |

#### RAG Quality Metrics
| Metric | What it tells you |
|--------|-------------------|
| Retrieval similarity score (P50, P10) | Is vector search finding relevant chunks? |
| Semantic cache hit rate | Cost savings + latency reduction |
| Fallback rate (score < 0.7) | How often RAG confidence is too low |
| Chunk age at retrieval | Are we serving stale knowledge base content? |
| Re-ranker score distribution | Quality of final chunk selection |

**Key degradation pattern:**
```
Symptom: retrieval similarity scores dropping over weeks
Cause:   knowledge base updated but embedding model version drifted
Fix:     re-index all chunks when model version changes
Alert:   P50 similarity score drops > 10% week-over-week
```

#### NER & Slot Filling Metrics
| Metric | What it tells you |
|--------|-------------------|
| Slot fill rate on first turn | How often users provide complete queries |
| Avg clarification turns | Turns needed to fill slots |
| Entity extraction failure rate | NER struggling with new query patterns |
| Entity resolution rejection rate | Failed ownership checks (also a security signal) |

---

### Layer 3 — Business / Product Metrics

```
Containment Rate = sessions resolved without human escalation
                   Target: > 80%  (most important single metric)
```

| Metric | Definition | Target |
|--------|------------|--------|
| **Containment rate** | % sessions resolved without escalation | > 80% |
| **Escalation rate** | % sessions routed to human agent | < 20% |
| **Session completion rate** | User got answer and left satisfied | > 75% |
| **Abandonment rate** | User left mid-session without resolution | < 15% |
| **CSAT** | Post-session thumbs up/down | > 4.2/5 |
| **Avg turns to resolution** | Messages needed to answer the question | < 3 |
| **Intent distribution** | Which intents are most common | capacity planning |
| **Language distribution** | Which languages in use | coverage gaps |

#### Session Funnel
```
Sessions started
      ↓ intent classified
Intent understood
      ↓ slots filled
Query executable
      ↓ answer returned
Answer satisfactory   ← CSAT signal
      ↓
Contained             ← containment rate
      OR
Escalated             ← escalation rate
```
Drop-offs between stages pinpoint exactly where the chatbot is failing.

---

### Layer 4 — Security Metrics

| Metric | Alert |
|--------|-------|
| Prompt injection detections/min | Spike > baseline × 3 → investigate |
| Scope violation attempts | Any surge → potential coordinated attack |
| Entity resolution rejections | High rate from single user → block + alert |
| Rate limit hits per user | Persistent hitting → flag for review |
| Content filter blocks (Azure OAI) | Track by category (hate, self-harm, etc.) |
| Auth failures at gateway | Spike → credential stuffing attempt |

---

### Alerting Severity

```
P1 — Page on-call immediately
  - Error rate > 5% for > 2 min
  - Queue age > 60s (users getting no response)
  - Azure OpenAI unavailable in both regions
  - Entity resolution rejection spike > 10× baseline

P2 — Slack alert, fix within 1 hour
  - P95 latency > 3s for > 5 min
  - PTU utilization > 90%
  - Containment rate drops > 10% in 1 hour
  - Semantic cache hit rate drops > 20%

P3 — Dashboard warning, fix next business day
  - RAG similarity score declining week-over-week
  - Specific language CSAT below 3.5
  - Slot fill failure rate trending up
```

---

### Tooling Stack

| Tool | Purpose |
|------|---------|
| Azure Monitor + App Insights | Infrastructure + LLM API metrics (native integration) |
| Prometheus + Grafana | Custom AI quality metrics, business dashboards |
| Azure Log Analytics | Audit logs, security events, PSD2 compliance queries |
| PagerDuty | P1/P2 alerting, on-call rotation |

**Four Dashboards:**
| Dashboard | Audience | Refresh |
|-----------|----------|---------|
| Operations | On-call engineer | Real-time |
| AI Quality | ML/AI team | 5 min |
| Business | Product manager | Hourly |
| Security | Security team | Real-time |

---

### Token Cost per Intent (Non-Obvious)

Track Azure OpenAI cost broken down by intent type:

| Intent | Avg Tokens | Cost Driver |
|--------|------------|-------------|
| balance_query | ~800 | Low |
| transaction_history | ~1,200 | Medium |
| kb_lookup | ~2,800 | High — RAG chunks inflate context |
| multi-turn complex | ~4,500 | Highest |

A 10% reduction in `kb_lookup` cost saves more than a 10% reduction in `balance_query`. Use this to prioritize caching and template investments.

---

## Model Serving

### Model Inventory

| Model | Owned by us? | Size | Traffic |
|-------|-------------|------|---------|
| GPT-4o | Azure OpenAI | — | All complex queries |
| text-embedding-3-large | Azure OpenAI | — | All RAG queries |
| Intent classifier | Us | ~66M params | 33k req/sec |
| NER model | Us | ~110M params | 33k req/sec |
| Prompt injection classifier | Us | ~66M params | 33k req/sec |
| Re-ranker (cross-encoder) | Us | ~110M params | ~10k req/sec |
| Sentiment classifier | Us | ~66M params | ~5k req/sec |

Azure OpenAI serving is their problem. Our problem is everything else.

---

### Latency Budget

```
Language detection (Azure CS):   ~10ms
Intent + prompt injection cls:    ~8ms   ← parallel
NER model:                        ~15ms
Redis cache check:                ~5ms
RAG retrieval (pgvector):         ~100ms
Re-ranker:                        ~60ms
Core Banking API:                 ~50ms
Azure OpenAI (TTFT, streaming):   ~200ms ← user sees tokens here
Response assembly:                ~10ms
──────────────────────────────────────
Total to first token:             ~458ms  ✓ well within 2s budget
```

---

### CPU + ONNX Runtime — No GPU Needed

All custom models are small BERT-class. ONNX Runtime on CPU is 2-5× faster than raw PyTorch:

```
Training (offline):
  PyTorch model → export to ONNX → ORT optimizer → INT8 quantization
                                                  → 4× smaller, 2× faster

Serving (online):
  ONNX Runtime inference server on CPU nodes (AKS)
```

INT8 quantized DistilBERT: ~8ms latency, ~17MB model size. No expensive GPU nodes required.

### Inference Service Architecture

```
[Orchestration Service]
         |
      gRPC  ← protobuf, ~5× smaller than JSON at 33k req/sec
         ↓
[Inference Gateway]
   /      |      \
  ↓       ↓       ↓
[Intent] [NER]  [Reranker]
  Svc     Svc     Svc
 (AKS)   (AKS)   (AKS)
```

---

### Per-Model Strategy

**Intent + Prompt Injection + NER (33k req/sec each)**
- No batching — latency target too tight, batching overhead exceeds savings
- Horizontal scale via HPA on CPU utilization
- Intent + prompt injection run in parallel (both needed before proceeding)

**Re-ranker (10k req/sec)**
- Dynamic batching: collect requests in 10ms window → single forward pass → N results
- Trade-off: +10ms latency, ~60% compute saving — worth it at this scale

**Sentiment classifier (5k req/sec)**
- Escalation path only — lower throughput, no special strategy needed

---

### Parallel Inference

Run independent classifiers concurrently to save latency:

```
User message arrives
        ↓
┌──────────────────────────┐
│ Intent classifier        │  ← parallel (~8ms total, not 23ms sequential)
│ Prompt injection cls     │  ← parallel
│ Language detection       │  ← parallel
└──────────────────────────┘
        ↓
      NER model
        ↓
   Slot filling
        ↓
  ┌──────────────┐
  │ RAG retrieval │  ← parallel where possible
  │ Core Banking  │  ← parallel where possible
  └──────────────┘
        ↓
     Re-ranker
        ↓
    Azure OpenAI (streaming)
```

---

### Canary Deployments

Every model update goes through canary — a bad intent classifier misrouting "fraud report" as "FAQ" is a serious incident:

```
v2 intent classifier deployed
        ↓
5% traffic → v2  |  95% traffic → v1
        ↓
Monitor 30 min:
  - Accuracy vs v1 baseline
  - Latency regression
  - Escalation rate change  ← key signal for misclassification
        ↓
Good? → 25% → 50% → 100%
Bad?  → instant rollback
```

Shadow mode for major changes: v2 runs on all traffic, results logged not served — compare offline before any live exposure.

### Model Registry (Azure ML)

```json
{
  "model_id": "intent-classifier",
  "version": "2.4.1",
  "accuracy": 0.947,
  "p95_latency_ms": 8.2,
  "test_dataset_hash": "sha256:abc123",
  "deployed_at": "2026-04-12T09:00:00Z"
}
```

Rollback = point deployment to previous version tag. No retraining required.

---

### Cold Start — Never Scale to Zero

Model load time is 3-8s. At 33k req/sec a cold pod receiving traffic causes cascading timeouts:

```yaml
minReplicas: 3          # always warm, never scale to 0
readinessProbe:
  initialDelaySeconds: 10  # wait for model load before routing traffic
```

Pods not marked ready until model is loaded and a warmup inference has passed.

---

### Serving SLA Summary

| Model | P95 Target | Throughput | Strategy |
|-------|------------|------------|----------|
| Intent classifier | < 10ms | 33k/s | ONNX + CPU + HPA |
| NER | < 20ms | 33k/s | ONNX + CPU + HPA |
| Prompt injection | < 8ms | 33k/s | ONNX + CPU + HPA |
| Re-ranker | < 80ms | 10k/s | ONNX + CPU + dynamic batching |
| Sentiment | < 12ms | 5k/s | ONNX + CPU + HPA |
| Azure OpenAI TTFT | < 250ms | 6.6k/s | PTU + streaming |

---

## Deployment

### Environment Strategy

```
dev → staging → prod

dev:      feature branches, shared infra, mocked Core Banking
staging:  production mirror (10% capacity min), real Azure OpenAI, real pgvector
prod:     live traffic, 50M users
```

Staging is a true production mirror — latency bugs only appear under real-scale configurations.

---

### CI/CD Pipeline

```
[PR opened]
     ↓
[Unit + integration tests]        ← gate 1: must pass
[Security scan (SAST)]            ← gate 2: no high/critical findings
[Docker image build]
[Push to Azure Container Registry]
     ↓
[Deploy to staging]
[Smoke tests]                     ← gate 3: golden path queries pass
[Load test (k6)]                  ← gate 4: P95 latency within budget
     ↓
[Manual approval — 2 engineers]   ← gate 5: banking four-eyes requirement
     ↓
[Deploy window check]             ← gate 6: not in frozen period
     ↓
[Deploy to prod — Blue/Green]
[Automated rollback monitor 15min] ← gate 7: auto-rollback on spike
```

Two-engineer approval is a banking compliance requirement. Logged immutably in audit trail.

---

### Deployment Strategies

#### Blue/Green — Major Releases
```
                    [Load Balancer]
                    /             \
              100% traffic      0% traffic
                  ↓                  ↓
            [Blue — v1]        [Green — v2]
            (current prod)     (fully warmed up)
```
Cutover = flip load balancer. Green fully warmed (models loaded, caches primed) before receiving traffic. Rollback = flip back. Takes seconds.

#### Rolling — Minor Updates
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 25%          # spin up 25% new pods before killing old
    maxUnavailable: 0      # never reduce capacity during rollout
```

#### Pod Disruption Budget
```yaml
spec:
  minAvailable: 70%        # always keep 70% pods running during maintenance
```

---

### Infrastructure as Code

**Bicep (Azure-native)** over Terraform — everything is Azure, no state file drift risk:

```
infra/
  ├── modules/
  │     ├── aks.bicep
  │     ├── azure-openai.bicep
  │     ├── redis.bicep
  │     ├── postgres.bicep
  │     ├── servicebus.bicep
  │     └── keyvault.bicep
  ├── environments/
  │     ├── staging.bicepparam
  │     └── prod.bicepparam
  └── main.bicep
```

Every resource change goes through PR + approval. No manual portal clicks — ever.

---

### Database Migrations — Expand/Contract

Never break running pods mid-deploy:

```
Phase 1 — Expand:   add new column (nullable) — old + new code both work
Phase 2 — Migrate:  backfill new column, verify integrity
Phase 3 — Contract: remove old column (after new code fully deployed)
```

Vector index built concurrently — never locks the table:
```sql
CREATE INDEX CONCURRENTLY idx_chunks_embedding
ON chunks USING hnsw (embedding vector_cosine_ops);
```

Migrations managed by **Flyway** — versioned, checksum-verified, run before pod rollout:
```
V001__initial_schema.sql
V002__add_language_metadata.sql
V003__add_jurisdiction_column.sql
```

---

### Secrets Management

```
[Azure Key Vault]
       ↑  Managed Identity (no passwords)
[AKS pods] → secrets mounted via CSI driver as env vars
```

Secret rotation: new version in Key Vault → CSI driver propagates to pods without restart → old version valid 24h → disabled after all pods confirmed updated. Zero-downtime.

---

### Deployment Windows

```
Standard deploys:    Tue/Wed 02:00–04:00 CET  (lowest EU traffic)
Emergency patches:   Any time, P1 only, CTO + Security sign-off
Frozen periods:      Month-end (last 3 days)
                     Salary processing days
                     Public holidays
                     Major regulatory reporting dates
```

Pipeline checks deployment calendar automatically before proceeding to prod gate.

---

### Rollback Strategy

| Layer | Mechanism | Time |
|-------|-----------|------|
| Application code | `kubectl rollout undo deployment/orchestration` | < 60s |
| ML models | Azure ML registry: point to previous version | < 30s |
| Infrastructure | Bicep redeploy previous commit | ~10 min |
| Database migration | Flyway down scripts (always written) | data-dependent |

**Automated rollback trigger:**
```
Post-deploy monitor (15 min):
  if error_rate > 2× pre-deploy baseline
  OR p95_latency > 2× pre-deploy baseline:
    → auto-rollback triggered
    → on-call paged
    → incident created
```
Human rollback only for database changes — automated rollback never touches data.

---

### Audit Trail (PSD2 / Banking Requirement)

Every deployment logged immutably in Azure Log Analytics (5-year retention):

```json
{
  "deploy_id": "deploy_20260517_0312",
  "service": "orchestration-service",
  "version": "v2.4.1",
  "environment": "prod",
  "approved_by": ["engineer_a", "engineer_b"],
  "deployed_by": "ci-pipeline",
  "deploy_time": "2026-05-17T03:12:00Z",
  "previous_version": "v2.4.0",
  "change_ticket": "CHG-4821"
}
```

---

### Deployment Flow Summary

```
[Feature branch]
      ↓ PR
[Tests + SAST + image build]
      ↓ merge to main
[Auto-deploy to staging]
      ↓ smoke + load tests pass
[Manual approval × 2]
      ↓ deploy window check
[Blue/Green deploy to prod]
      ↓ 15min automated monitor
Stable   → old blue torn down
Unstable → auto-rollback → incident created
```

---

## Human Escalation — Queue Management

### Escalation Triggers
```
confidence < 0.7
user_sentiment == "angry"
topic == "fraud" OR "complaint"
3+ consecutive fallback responses
user explicitly requests human
```

### Priority Queue Architecture

Four queues on Azure Service Bus — separate agent pools per priority:

```
[Escalation Trigger]
        ↓
[Priority Classifier]
        ↓
┌──────────────────────────────────────┐
│ P1: Fraud / Security    SLA: < 2 min │  dedicated agents, 24/7
│ P2: Complaints/Disputes SLA: < 5 min │  regulatory pressure
│ P3: Complex queries     SLA: <10 min │  general agents
│ P4: General escalations SLA: <15 min │  any available agent
└──────────────────────────────────────┘
```

P1 fraud queue never competes with P4 general questions for agent capacity.

### Queue Message Schema

```json
{
  "escalation_id": "esc_abc123",
  "user_id": "hashed_uid",
  "session_id": "sess_xyz",
  "priority": "P2",
  "reason": "complaint",
  "language": "de",
  "required_skill": "complaints_handling",
  "enqueued_at": "2026-05-17T10:23:00Z",
  "context": {
    "conversation_summary": "User disputing €450 charge on 12 May...",
    "last_4_turns": [...],
    "accounts_referenced": ["ACC_789"],
    "intent_history": ["transaction_query", "dispute_initiation"]
  }
}
```

Agent receives full context — customer never repeats themselves.

### Routing Logic

Two dimensions: **skill** + **language**:
```
[P2, lang=de, skill=complaints]
        ↓
find: available + speaks DE + certified complaints handling
  → found    → assign immediately
  → no skill → DE speaker (any skill) + supervisor flag
  → no DE    → EN speaker + translation note attached
```

Language matching is best-effort — waiting 25 min for a German agent is worse than an English agent with a translation note.

### Wait Time Management

```
Bot: "Connecting you with a specialist. Estimated wait: 4 minutes.
      I'll stay here — feel free to ask me anything while you wait."

if estimated_wait > 10 min:
  Bot: "Would you prefer a callback instead?
        We can reach you at your registered number within 2 hours."
```

Chatbot remains active during wait. Queue position updated every 60 seconds.

### Overflow & After-Hours

```
Business hours (08:00–20:00 CET):
  → normal queue routing

Peak overflow (queue age > SLA threshold):
  → offer callback scheduling
  → P1/P2 routed live regardless

After hours:
  P1 Fraud → 24/7 dedicated fraud team (always staffed)
  P2–P4    → scheduled callback next business day
             + email confirmation with ticket number (PSD2 audit trail)
```

### Agent Interface

Agent sees a single pane — same chat window the customer is in:

```
┌─────────────────────────────────────────────┐
│ Customer: [display name]     Language: DE   │
│ Priority: P2 — Complaint     Wait: 3m 42s   │
├─────────────────────────────────────────────┤
│ SUMMARY                                     │
│ "Disputing €450 charge on 12 May,           │
│  merchant: AMZN, says never made purchase"  │
├─────────────────────────────────────────────┤
│ ACCOUNT CONTEXT                             │
│ ACC_789 — Checking, ending 1332             │
│ Flagged transaction: €450 / 12 May          │
├─────────────────────────────────────────────┤
│ FULL CHAT HISTORY ↓                         │
└─────────────────────────────────────────────┘
```

### Dead Letter Queue

Messages failing routing after 3 retries:
```
→ Supervisor alert (immediate)
→ Auto-schedule callback within 1 hour
→ Customer notified by push notification
```
No escalation silently dropped — every entry accounted for.

### SLA Monitoring

```
Metrics per queue:
  - Current depth
  - Age of oldest message   ← primary SLA signal
  - Average handle time
  - Abandonment rate
  - First contact resolution rate

Alerts:
  P1 queue age > 90s  → page supervisor immediately
  P2 queue age > 4min → Slack alert to team lead
  Any dead letter     → immediate supervisor alert
```

---

## Areas for Further Design
- [ ] Knowledge base update pipeline (doc versioning, re-indexing)
