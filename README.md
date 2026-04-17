# Amazon E-commerce Support Agent

A conversational AI agent powered by **AWS Bedrock** and **LangChain** that provides intelligent customer support for Amazon e-commerce operations. The agent can answer questions about company documents (10-K filings) and check customer order status with secure information handling.

## Features

- **Document Retrieval & QA**: Leverages RAG (Retrieval-Augmented Generation) to answer questions about company 10-K reports
- **Order Status Checking**: Securely retrieves customer order information using order verification
- **Multi-turn Conversations**: Maintains conversation context with intelligent history management
- **Sensitive Data Protection**: Automatically masks SSN, date of birth, and personal information
- **Conversation Logging**: Saves sanitized conversation history for audit purposes
- **Web UI**: Interactive Streamlit interface for easy access

## Architecture

```
┌─────────────────┐
│   Streamlit UI  │
│   (app.py)      │
└────────┬────────┘
         │
    ┌────▼────────────────────────┐
    │   Agent (agent.py)          │
    │  - Multi-turn conversation  │
    │  - Tool orchestration       │
    └────┬──────────┬──────────────┘
         │          │
    ┌────▼───┐   ┌──▼──────────────┐
    │Retriever│   │Bedrock Client   │
    │(RAG)   │   │- Claude 3 Haiku │
    │- FAISS │   │- Embeddings     │
    └────────┘   └─────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **UI Framework** | Streamlit |
| **LLM Provider** | AWS Bedrock (Claude 3 Haiku) |
| **Embeddings** | Amazon Titan Embed Text v2 |
| **Vector DB** | FAISS |
| **Document Processing** | PyPDF, pdfplumber |
| **Framework** | LangChain, LangChain Community |
| **AWS SDK** | boto3 |

## Prerequisites

- **Python 3.8+**
- **AWS Account** with Bedrock access (us-east-1)
- **AWS Credentials** configured (via `~/.aws/credentials` or environment variables)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd project
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your settings:
   ```env
   # AWS Configuration
   AWS_REGION=us-east-1
   
   # PDF Configuration
   PDF_PATH=data/Company-10k-18pages.pdf
   
   # Retrieval Settings (optional)
   SIMILARITY_THRESHOLD=0.7
   LOG_RETRIEVAL_SCORES=true
   ```

5. **Prepare data**
   - Place your 10-K PDF in the `data/` directory
   - Name it as specified in `PDF_PATH` (default: `Company-10k-18pages.pdf`)

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open at `http://localhost:8501`

### Asking Questions

1. **Ask about company information**: "What are the main products discussed in the 10-K?"
2. **Check order status**: "My name is John Doe, SSN last 4 is 1234, DOB is 1990-01-01. What's my order status?"

The agent will:
- Extract relevant information from your question
- Retrieve matching sections from the 10-K document
- Call appropriate tools when needed
- Provide a comprehensive answer with context

### Conversation Management

- **Clear History**: Click the "🗑️ Clear history" button to start fresh
- **Auto-save**: Conversations are automatically saved to `conversations/latest_conversation.json`
- **Data Protection**: Sensitive information is masked before saving

## Configuration

All configuration is managed through `config.py`:

```python
# Bedrock Models
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
LLM_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Retrieval Parameters
CHUNK_SIZE = 1500              # Text chunk size for embeddings
CHUNK_OVERLAP = 300            # Overlap between chunks
TOP_K = 3                      # Number of documents to retrieve
SIMILARITY_THRESHOLD = 0.7     # Optional: filter low-confidence results

# Data Paths
PDF_PATH = "data/Company-10k-18pages.pdf"
FAISS_INDEX_PATH = "data/faiss.faiss"
```

## Project Structure

```
project/
├── app.py                    # Streamlit UI application
├── agent.py                  # Conversational agent with tool calling
├── retriever.py             # PDF retrieval with FAISS vectorstore
├── bedrock_client.py        # AWS Bedrock API wrapper
├── config.py                # Configuration management
├── mock_api.py              # Mock order status API
├── requirements.txt         # Python dependencies
├── prompt.txt               # System prompt for Claude
├── .env                     # Environment variables (not versioned)
├── conversations/           # Conversation logs
├── data/                    # PDF files and FAISS indices
└── text/                    # Text processing utilities
```

## Key Components

### PDFRetriever
Handles document loading, chunking, and semantic search using FAISS vector store:
- Loads PDF and splits into chunks
- Embeds chunks using Bedrock embeddings
- Retrieves top-K similar documents for user queries
- Optional similarity threshold filtering

### Agent
Orchestrates multi-turn conversations with tool calling:
- Maintains message history (max 20 messages)
- Parses user input for order information
- Invokes Bedrock API with system prompt and tools
- Handles tool use responses (order status checking)
- Resets state after successful tool execution

### BedrockClient
Wrapper for AWS Bedrock API:
- Text embedding generation
- Model invocation with conversation history
- Tool configuration and response parsing

## Security Considerations

- **Data Masking**: SSN, DOB, and order identifiers are masked in logs
- **Tool Validation**: Order status tool requires all three fields (name, SSN, DOB)
- **No Secret Storage**: Sensitive data is not persisted in plain text
- **AWS IAM**: Use IAM roles/policies to restrict Bedrock access

## Error Handling

The application handles common errors gracefully:
- Missing PDF file → Disables retrieval with warning
- Bedrock API failures → Returns user-friendly error message
- Malformed tool inputs → Rejects and asks for clarification
- Orphaned tool states → Auto-clears conversation on recovery

## Performance Optimization

- **FAISS Index Caching**: Vectorstore is built once and reused
- **Session State Caching**: Retriever initialized once per Streamlit session
- **Chunk Overlap**: Ensures context continuity across semantic boundaries
- **History Trimming**: Maintains only last 20 messages to reduce token usage

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "FAISS index not found" | Run the app once to build the index from PDF |
| "Bedrock call failed" | Verify AWS credentials and Bedrock model access |
| "PDF not found" | Ensure PDF is at `data/Company-10k-18pages.pdf` |
| "Empty context returned" | Adjust `SIMILARITY_THRESHOLD` or `TOP_K` in config |
| "Order info not recognized" | Provide all three fields in format: "Name, SSN last 4, DOB (YYYY-MM-DD)" |

## AWS Setup Guide

### 1. Enable Bedrock Models

```bash
# List available models
aws bedrock list-foundation-models --region us-east-1

# Request model access if needed
# - anthropic.claude-3-haiku-20240307-v1:0
# - amazon.titan-embed-text-v2:0
```

### 2. Configure AWS Credentials

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables
export AWS_ACCESS_KEY_ID=your_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

## Development

### Adding New Tools

1. Define tool schema in `agent.py`:
   ```python
   NEW_TOOL = {
       "toolSpec": {
           "name": "tool_name",
           "description": "...",
           "inputSchema": { ... }
       }
   }
   ```

2. Implement tool handler in `agent.py`

3. Add to tools list in `converse()` call

### Running Tests

```bash
# Unit tests (if available)
pytest tests/

# Manual testing
streamlit run app.py
```

## Contributing

Contributions welcome! Please:
1. Create a feature branch
2. Make changes with clear commit messages
3. Test thoroughly before submitting PR
4. Follow existing code style

## License

[Specify your license here]

## Support

For issues or questions:
- Check the troubleshooting section above
- Review AWS Bedrock documentation: https://docs.aws.amazon.com/bedrock/
- Check LangChain docs: https://python.langchain.com/

## Changelog

### Version 1.0.0
- Initial release
- Multi-turn conversation support
- Order status checking tool
- Document Q&A with FAISS retrieval
- Sensitive data masking
