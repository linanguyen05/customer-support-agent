# Amazon E-commerce Support Agent

An AI customer support agent powered by AWS Bedrock and LangChain, with two core capabilities:

- Knowledge-based Q&A from internal documents (Amazon 10-K) using RAG.
- Order status lookup through a tool-calling workflow with identity verification.

The app uses Streamlit for UI, supports multi-turn conversations, stores masked conversation logs, and includes Terraform infrastructure for AWS deployment.

## Table of Contents

- [Amazon E-commerce Support Agent](#amazon-e-commerce-support-agent)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Architecture](#architecture)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)
  - [System Requirements](#system-requirements)
  - [Local Setup and Run](#local-setup-and-run)
    - [1) Clone repository](#1-clone-repository)
    - [2) Create and activate virtual environment](#2-create-and-activate-virtual-environment)
    - [3) Install dependencies](#3-install-dependencies)
    - [4) Create `.env`](#4-create-env)
    - [5) Start the app](#5-start-the-app)
  - [Environment Configuration](#environment-configuration)
  - [AWS Deployment with Terraform](#aws-deployment-with-terraform)
    - [What Terraform provisions](#what-terraform-provisions)
    - [Deployment steps](#deployment-steps)
    - [Post-demo security note](#post-demo-security-note)
  - [Security](#security)
  - [Operations and Troubleshooting](#operations-and-troubleshooting)
  - [Suggested Roadmap](#suggested-roadmap)
  - [License](#license)

## Features

- Answers questions using retrieved context from PDF documents (RAG + FAISS).
- Calls `check_order_status` only when all 3 required fields are present: `full_name`, `ssn_last4`, `dob`.
- Supports multi-turn dialogue with a capped message history (20 messages) to control token usage.
- Masks sensitive data before writing chat logs (`SSN`, `DOB`, identity-like patterns).
- Supports streaming responses for knowledge-only questions (no tool call).
- Includes Terraform provisioning for EC2, IAM, Security Group, and Elastic IP.

## Architecture

```text
Browser
  -> Streamlit UI (app.py)
      -> Agent (agent.py)
          -> BedrockClient (bedrock_client.py)
              -> Claude 3 Haiku (chat)
              -> Titan Embed v2 (embeddings)
          -> PDFRetriever (retriever.py)
              -> FAISS index (local /tmp/faiss_data)
              -> S3 (PDF + FAISS artifacts)
          -> mock_order_status tool (mock_api.py)
```

Main request flow:

1. User sends a question from the UI.
2. Agent retrieves context through the retriever.
3. Agent calls Bedrock Converse with system prompt and tool schema.
4. If the model requests tool use: validate input, execute mock API, return `toolResult`.
5. Return final answer and persist masked conversation history.

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | AWS Bedrock - Anthropic Claude 3 Haiku |
| Embeddings | Amazon Titan Embed Text v2 |
| Retrieval | LangChain + FAISS |
| PDF parsing | pdfplumber, pypdf |
| AWS SDK | boto3 |
| IaC | Terraform |

## Project Structure

```text
project_clean/
├── app.py
├── agent.py
├── bedrock_client.py
├── retriever.py
├── mock_api.py
├── config.py
├── prompt.txt
├── requirements.txt
├── conversations/
├── data/
├── docs/
└── terraform/
```

## System Requirements

- Python 3.10+ (recommended).
- AWS account with Bedrock access in `us-east-1`.
- Model access enabled for:
  - `anthropic.claude-3-haiku-20240307-v1:0`
  - `amazon.titan-embed-text-v2:0`
- Valid AWS credentials (AWS CLI profile or environment variables).

## Local Setup and Run

### 1) Clone repository

```bash
git clone https://github.com/linanguyen05/customer-support-agent.git
cd customer-support-agent
```

### 2) Create and activate virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Create `.env`

Minimal example based on current implementation:

```env
AWS_REGION=us-east-1

S3_BUCKET=support-agent-data-la-ck
S3_PDF_KEY=data/Company-10k-18pages.pdf
S3_INDEX_PREFIX=data/

LOCAL_TMP=/tmp/faiss_data

LOG_RETRIEVAL_SCORES=true
# SIMILARITY_THRESHOLD=0.7
```

Notes:

- `retriever.py` downloads the PDF and FAISS artifacts from S3 if not already available locally.
- If running without S3, ensure these files already exist in `LOCAL_TMP`:
  - `Company-10k-18pages.pdf`
  - `faiss.faiss`
  - `faiss.pkl`

### 5) Start the app

```bash
streamlit run app.py
```

Default URL: `http://localhost:8501`

## Environment Configuration

Key variables in `config.py`:

| Variable | Description | Default |
|---|---|---|
| `AWS_REGION` | Bedrock region | `us-east-1` |
| `S3_BUCKET` | Bucket for PDF/index artifacts | empty |
| `S3_PDF_KEY` | PDF object key | `data/Company-10k-18pages.pdf` |
| `S3_INDEX_PREFIX` | Prefix for FAISS artifacts | `data/` |
| `LOCAL_TMP` | Local cache folder | `/tmp/faiss_data` |
| `TOP_K` | Number of retrieved chunks | `3` |
| `CHUNK_SIZE` | Chunk size | `1500` |
| `CHUNK_OVERLAP` | Chunk overlap | `300` |

## AWS Deployment with Terraform

Infrastructure directory: `terraform/`

### What Terraform provisions

- Ubuntu 22.04 EC2 instance.
- Elastic IP associated to EC2.
- Security Group opening ports `22` and `8501`.
- IAM Role/Instance Profile for `s3:GetObject`, `s3:ListBucket`, Bedrock invoke actions.
- User data automation that:
  - clones the repository,
  - installs dependencies,
  - pulls data from S3,
  - creates `.env`,
  - runs Streamlit as a `systemd` service.

### Deployment steps

```bash
cd terraform
terraform init
terraform plan -out tfplan
terraform apply tfplan
```

After apply, read outputs:

```bash
terraform output ec2_public_ip
terraform output streamlit_url
terraform output ssh_command
```

### Post-demo security note

- Security Group currently allows `0.0.0.0/0` for SSH and Streamlit for demo convenience.
- Restrict CIDR to trusted admin IP ranges before production use.

## Security

- Sensitive values are masked before writing `conversations/latest_conversation.json`.
- Order-status tool requires all 3 identity fields in valid formats.
- No hardcoded AWS secrets in source code.
- Using IAM role on EC2 is recommended over static access keys.

## Operations and Troubleshooting

| Issue | Common Cause | Resolution |
|---|---|---|
| Bedrock `AccessDenied` | Missing model access or IAM permission | Verify Bedrock model access and IAM policy |
| No retrieval context | Missing FAISS/PDF locally and incorrect S3 keys | Check `S3_BUCKET`, `S3_PDF_KEY`, `S3_INDEX_PREFIX`, and S3 objects |
| Streamlit unavailable on EC2 | Service failure or closed port | Run `sudo systemctl status streamlit` and verify SG port 8501 |
| Order tool not executed | Missing `full_name`, `ssn_last4`, or `dob`, or invalid format | Provide all fields with `YYYY-MM-DD` DOB and 4-digit SSN |

Useful EC2 commands:

```bash
sudo systemctl status streamlit
sudo journalctl -u streamlit -n 100 --no-pager
tail -n 100 /home/ubuntu/agent_debug.log
```

## Suggested Roadmap

- Add intent classification for mixed questions (knowledge + order).
- Persist conversation history in DynamoDB by `session_id`.
- Add metrics and tracing via CloudWatch + X-Ray.
- Re-enable CI/CD with GitHub Actions (test + deploy pipeline).

## License

This project is currently for assignment/internal learning purposes. Add an explicit `LICENSE` file before public production distribution.
