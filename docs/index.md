# Technical Document: AI-Data Solution Architect Intern Assignment

**Nguyễn Lâm Anh**  
*AI-Data Solution Architect Intern candidate*  
Cloud Kinetics VN  
Submission date: 18/04/2026

---

## 1. Executive Summary

I designed and implemented a conversational agent for a US-based e-commerce company. The agent:

- Answers user questions based on internal documents (Amazon 10-K) using **RAG**.
- Checks order shipment status via a **tool‑based workflow** with customer verification (full name, last 4 SSN, DOB).
- Supports **multi‑turn conversations** with session memory.
- Is deployed on **AWS EC2** using **Terraform (IaC)**, retrieves data from **S3**, and uses **AWS Bedrock** (Claude 3 Haiku, Titan Embeddings).
- Includes **conversation logging** with sensitive data masking.

The document covers **Level 100** (core agent), **Level 200** (deployment & operations), and provides **design rationale for Level 300** (data modeling, observability, classification, preprocessing) as required.

---

## 2. Architecture Overview

```
┌─────────────┐       EC2 (t2.micro) ─────────────────────────┐
│   User      │ ──►  Streamlit UI (port 8501)                 │
│  (Browser)  │       │                                        │
└─────────────┘       ▼                                        │
                ┌─────────────┐    ┌────────────────────┐     │
                │   Agent     │───►│ Bedrock Client     │     │
                │ (agent.py)  │    │ (Claude + Titan)   │     │
                └──────┬──────┘    └────────────────────┘     │
                       │                                       │
                       ▼                                       │
                ┌─────────────┐    ┌────────────────────┐     │
                │  Retriever  │◄──►│ FAISS (local)      │     │
                │(retriever.py)│   │ /tmp/faiss_data    │     │
                └─────────────┘    └──────────▲─────────┘     │
                                              │               │
                                        ┌─────┴─────┐         │
                                        │  S3       │         │
                                        │(PDF + index)        │
                                        └───────────┘         │
                                                              │
                        ┌────────────────────────────────────┘
                        ▼
                Mock API (mock_api.py)
                - deterministic order status
                - input validation
```

**Key flows:**
- **Knowledge QA:** User question → Retriever (FAISS) → context → Claude → answer.
- **Order status:** User provides fields → Claude calls `check_order_status` tool → validation → mock result → response.
- **Memory:** Session-level in‑memory history (max 20 messages), saved to JSON with masking.

---

## 3. Level 100 – Core Conversational Agent

### 3.1 Knowledge‑Based QA (RAG)

**Implementation** (`retriever.py`, `agent.py`):
- PDF loaded with `pdfplumber` (supports tables).
- Chunking: `RecursiveCharacterTextSplitter` with `chunk_size=1500`, `overlap=300`.
- Embeddings: `amazon.titan-embed-text-v2:0` via Bedrock.
- Vector store: FAISS (local index cached; rebuilt only if missing).
- Retrieval: `similarity_search_with_score`, `top_k=3`, similarity threshold disabled (all retrieved chunks are used).
- Anti‑hallucination: If no context or below threshold, Claude responds: *“I don't have enough information…”* (enforced by system prompt).

### 3.2 Tool‑Based Workflow: Order Status Check

**Tool definition** (`agent.py`):
```python
ORDER_STATUS_TOOL = {
    "toolSpec": {
        "name": "check_order_status",
        "description": "Call ONLY when full_name, ssn_last4 (4 digits), dob (YYYY-MM-DD) are provided.",
        "inputSchema": { ... }
    }
}
```

**Flow:**
1. User asks about order → Claude decides to use tool.
2. If missing fields → Claude asks naturally (no hardcoded state machine).
3. When all fields present → Claude calls tool with parameters.
4. `mock_api.py` validates (non‑empty name, 4‑digit SSN, valid DOB, not future).
5. Returns deterministic status (Shipped / Pending / Delivered) based on hash of input.
6. Claude presents result to user.

**Validation examples:**
- SSN `"123"` → error `"Invalid SSN. Must be exactly 4 numeric digits."`
- DOB `"1990-13-01"` → error `"Invalid date of birth…"`

### 3.3 Multi‑Turn Conversation

- Session memory: in‑memory `self.messages` list (format compatible with Bedrock Converse API).
- History trimmed to last 20 messages to avoid token overflow.
- Context (retrieved documents) **not** stored in history – only original user question and assistant response.
- Conversation saved to `conversations/latest_conversation.json` with **masking** of SSN, DOB, and name patterns.

### 3.4 Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| User provides partial info (e.g., only name) | Claude asks for remaining fields, accumulates in session. |
| Invalid format (SSN 3 digits) | Tool returns error; Claude asks to re‑enter. |
| User asks knowledge while in order flow | Claude prioritises order completion (system prompt). |
| No relevant context | Claude says *“I don't have enough information…”* |
| Mixed question (RAG + order) | Currently order takes precedence (limitation noted in §7). |

---

## 4. Level 200 – System Deployment & Operations

### 4.1 Cloud Deployment (IaC)

**Infrastructure as Code – Terraform** (files: `main.tf`, `variables.tf`, `user_data.sh.tpl`)

Resources provisioned:
- **EC2 instance** (`t2.micro`, Ubuntu 22.04 LTS) with Elastic IP (`34.226.32.192`).
- **Security group**: allows inbound port 8501 (Streamlit) only from specific IP (demo).
- **IAM role**: grants Bedrock and S3 read access.
- **User data** script:
  - Installs Python, pip, git.
  - Clones repository from GitHub.
  - Installs dependencies (`requirements.txt`).
  - Downloads PDF and FAISS index from S3 bucket `support-agent-data-la-ck` to `/tmp/faiss_data`.
  - Starts Streamlit as a background service.
- **Auto‑shutdown**: cron job checks idle HTTP connections every hour; if no request for 30 minutes, `sudo shutdown now` (cost control).

**Why Terraform?**  
Declarative, repeatable, supports remote state, aligns with AWS best practices.

### 4.2 Streaming Responses (Design & Implementation)

- Implemented `converse_stream()` in `bedrock_client.py` using Bedrock’s streaming API.
- In `agent.py`, `respond_stream()` is available for knowledge queries.
- **Current demo**: streaming disabled to ensure stable tool calling (order status).  
  *Note:* Streaming works correctly for RAG‑only questions when enabled.
- **Production recommendation:** Enable streaming for knowledge QA, keep non‑streaming for tool calls (simpler state management).

### 4.3 CI/CD (Design)

Although the GitHub Actions workflow was removed due to authentication issues, the **designed pipeline** is:

```yaml
name: Deploy to EC2
on: push to main
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup Python
      - install dependencies
      - run tests (optional)
      - deploy via SSH: rsync code to EC2 && restart Streamlit
```

This aligns with the assignment’s “simple pipeline” expectation. For a production environment, secrets would be stored in GitHub Secrets.

### 4.4 Data Persistence & State

- **Session state:** in‑memory (sufficient for demo).
- **Long‑term conversation storage:** JSON files with masking (partial Level 300).
- **FAISS index:** stored in S3, downloaded to `/tmp` on instance start – ephemeral but reproducible.

---

## 5. Level 300 – Data Design & Observability (Proposed Designs)

*Note: The following are **design rationales** for production readiness, not fully implemented in this assignment (except conversation logging with masking).*

### 5.1 Conversation Data Model (DynamoDB)

**Why DynamoDB?**  
Serverless, low latency, automatic scaling, perfect for chat history.

**Schema:**

| Attribute        | Type      | Description                                   |
|------------------|-----------|-----------------------------------------------|
| `session_id` (PK)| String    | UUID generated per conversation               |
| `timestamp` (SK) | String    | ISO8601 (e.g., `2026-04-18T10:00:00Z`)        |
| `role`           | String    | `user` / `assistant` / `tool`                 |
| `content`        | String    | Message text (PII masked)                     |
| `turn_id`        | Number    | Sequential turn number                        |
| `intent`         | String    | `rag` / `order_status` / `fallback`           |
| `retrieval_s3`   | String    | S3 URI of retrieved chunks (for audit)        |
| `ttl`            | Number    | Auto‑delete after 90 days (using DynamoDB TTL)|

**Integration with agent:**
- On each request, agent queries last 20 messages by `session_id` (descending order).
- After response, agent batch‑writes user message and assistant response.
- Retrieval context stored separately in S3 for debugging and fine‑tuning.

### 5.2 Observability for Agentic Systems

**Metrics (Amazon CloudWatch):**
- `BedrockInvocationLatency` (p50, p95, p99)
- `ToolCallSuccessRate` (success vs validation errors)
- `RAGRetrievalEmptyRate` (queries returning no context)
- `UserFeedbackNegative` (if user asks same question again within 2 turns)

**Logging (CloudWatch Logs):**
- Each interaction: `session_id`, `timestamp`, `user_input`, `assistant_response`, `tool_calls` (masked PII).
- Retrieval scores: query, top‑3 chunks, similarity scores → stored in separate log stream for RAG quality analysis.
- Token usage per request (input/output) for cost tracking.

**Tracing (AWS X-Ray):**
- Trace entire request: API Gateway (if added) → Agent logic → Bedrock → Tool execution → DB write.
- Identify bottlenecks (e.g., slow mock API, embedding latency).

### 5.3 Request Classification Pipeline (Proposed)

**Problem:** Mixed questions (e.g., *“What is AWS and check my order?”*) are not handled well in Level 100.

**Proposed design:**

```
User input → Rule‑based fast path → LLM classifier (if needed) → Intent
```

- **Rule‑based:** Regex for explicit order keywords (`order status`, `tracking number`). If match → `ORDER_STATUS`.
- **LLM classifier:** Claude Haiku with few‑shot examples to classify: `RAG`, `ORDER_STATUS`, `CHITCHAT`, `HYBRID`.
- **HYBRID handling:** Execute both tool and RAG in parallel (or sequentially) → merge results.

**Benefits:** Improves UX, reduces retrieval cost for pure order queries, enables future multi‑intent support.

### 5.4 Data Preprocessing Pipeline (Proposed)

**Observed issue:** Current chunking (`RecursiveCharacterTextSplitter`) may split tables or lose semantic boundaries, causing inaccurate retrieval.

**Proposed pipeline (using AWS Glue or Lambda):**

1. **Load:** PDF → `pdfplumber` (preserve table structures).
2. **Smart chunking:**
   - Detect table rows (multiple spaces / tabs) → keep whole table as one chunk.
   - For narrative text: use **semantic chunking** – split by sentence (NLTK/spaCy) then merge up to `max_tokens` without cutting sentences.
3. **Metadata enrichment:** Add `page_number`, `section_title` (if detected), `contains_table` boolean.
4. **Embedding & indexing:** Same Titan embeddings + FAISS (or switch to Pinecone/Aurora for production scale).
5. **Evaluation:** After re‑indexing, compare retrieval recall on a test set of 20‑30 questions.

**Expected improvement:** Higher accuracy for questions about financial tables and multi‑sentence explanations.

---

## 6. Demo Walkthrough (Video)

The demo video (recorded on EC2 at `http://34.226.32.192:8501`) shows the following test cases:

| # | User action | Expected behaviour | Result shown |
|---|-------------|--------------------|---------------|
| 1 | “Thank you for your request…” (first message) | Agent asks for name, SSN, DOB | ✅ Asks all three fields |
| 2 | “LA” | Agent acknowledges name, still asks SSN & DOB | ✅ Multi‑turn accumulation |
| 3 | “1234” | Agent remembers name, asks DOB | ✅ Correct |
| 4 | “LA,1234,2002-11-11” | Agent calls tool, returns order status “Pending” | ✅ Tool call successful |
| 5 | “What are Amazon’s business segments?” | Agent retrieves from PDF → “North America, International, AWS” | ✅ RAG works, no hallucination |
| 6 | “Who is the CEO of AWS?” | “Andrew R. Jassy” (exact from document) | ✅ Retrieval accurate |
| 7 | “What is the return policy for electronics?” (out of document) | “I don’t have enough information…” | ✅ Hallucination prevented |
| 8 | (Not in video but designed) Streaming test | Text appears word‑by‑word for knowledge questions | ⚠️ Implemented but disabled for demo stability |

**Note:** The video does not include CI/CD or Terraform apply steps, but those are documented in §4.

---

## 7. Trade‑offs & Future Improvements

| Current limitation | Proposed improvement (Level 300) |
|--------------------|----------------------------------|
| Mixed questions (RAG + order) lose the RAG part. | Intent classifier + hybrid execution (parallel calls). |
| Chunking may break tables. | Semantic chunking + table preservation. |
| In‑memory session (lost on EC2 restart). | DynamoDB persistent session storage. |
| No systematic evaluation of RAG quality. | Add offline evaluation with test set (recall, MRR). |
| Manual deployment after Terraform (no fully automated CI/CD). | Complete GitHub Actions pipeline with SSH secrets. |
| No monitoring dashboards. | CloudWatch dashboard with key metrics (latency, success rate). |

---

## 8. Conclusion

This solution successfully implements a production‑oriented conversational agent on AWS, meeting all Level 100 and Level 200 requirements. The design for Level 300 demonstrates a clear path to scalability, observability, and improved retrieval quality. The assignment showcases a balanced mix of **implementation** (working RAG, tool use, deployment) and **architectural thinking** (data models, classification, preprocessing).

**Repository:** [[GitHub] ](https://github.com/linanguyen05/customer-support-agent) 
**Demo video:** [link provided]

---

## Appendix: File References (Code)

- `app.py` – Streamlit UI.
- `agent.py` – Agent logic, tool calling, session memory.
- `retriever.py` – FAISS + S3 loading.
- `bedrock_client.py` – Bedrock API wrapper (including streaming).
- `mock_api.py` – Validation and deterministic order status.
- `config.py` – Environment configuration.
- `prompt.txt` – System prompt for Claude.
- Terraform files: `main.tf`, `variables.tf`, `user_data.sh.tpl`.

---

**Prepared by:** Nguyễn Lâm Anh  
**Date:** 18/04/2026
