# Microservices Architecture

This chatbot has been refactored into a microservices architecture with separate Lambda functions for different responsibilities.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │───▶│  API Gateway     │───▶│  Orchestrator   │
│   (React)       │    │                  │    │  Lambda         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                       ┌─────────────────────────────────────────┐
                       │           Lambda Functions              │
                       │                                         │
                       │  ┌─────────────┐  ┌─────────────────┐  │
                       │  │ RAG Search  │  │ Document Mgmt   │  │
                       │  │ Lambda      │  │ Lambda          │  │
                       │  └─────────────┘  └─────────────────┘  │
                       │                                         │
                       │  ┌─────────────────────────────────┐  │
                       │  │ Response Enhancement Lambda     │  │
                       │  └─────────────────────────────────┘  │
                       └─────────────────────────────────────────┘
```

## Lambda Functions

### 1. Orchestrator Lambda (`chatbot-orchestrator`)
- **Purpose**: Main decision-making and coordination
- **Responsibilities**:
  - Claude AI decision making
  - Action planning and execution
  - Coordinating other lambdas
  - Conversation management
- **Dependencies**: All other lambdas

### 2. RAG Search Lambda (`chatbot-rag-search`)
- **Purpose**: Knowledge base search and embeddings
- **Responsibilities**:
  - Semantic search using sentence-transformers
  - Embedding generation
  - Vector similarity calculations
- **Dependencies**: DynamoDB, S3

### 3. Document Management Lambda (`chatbot-document-management`)
- **Purpose**: Document operations and metadata
- **Responsibilities**:
  - List documents
  - Get document content
  - Document metadata retrieval
  - Document search
- **Dependencies**: DynamoDB, S3

### 4. Response Enhancement Lambda (`chatbot-response-enhancement`)
- **Purpose**: Final response generation
- **Responsibilities**:
  - Claude AI response enhancement
  - Source extraction and formatting
  - Response polishing
- **Dependencies**: DynamoDB, Claude API

## Deployment

The microservices are automatically deployed via GitHub Actions when changes are pushed to the main branch.

### Required GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`
- `CLAUDE_API_KEY`

### ECR Repositories:
- `chatbot-orchestrator`
- `chatbot-rag-search`
- `chatbot-document-management`
- `chatbot-response-enhancement`

## API Endpoints

### POST /chat
Main chat endpoint that routes to the Orchestrator Lambda.

**Request:**
```json
{
  "action": "chat",
  "message": "Hello, how are you?",
  "conversation_id": "optional-conversation-id",
  "use_rag": true
}
```

**Response:**
```json
{
  "response": "AI response text",
  "sources": [
    {
      "chunk_id": "chunk-123",
      "document_id": "doc-456",
      "source": "document.pdf",
      "page_number": 1,
      "element_type": "text",
      "hierarchy_level": 2,
      "similarity_score": 0.85,
      "content": "Relevant content snippet",
      "metadata": {...}
    }
  ],
  "conversation_id": "conversation-789",
  "timestamp": "2024-01-01T00:00:00Z",
  "action_plan": {...},
  "needs_clarification": false
}
```

## Benefits of Microservices Architecture

1. **Scalability**: Each lambda can scale independently based on demand
2. **Maintainability**: Clear separation of concerns
3. **Fault Isolation**: Failure in one service doesn't affect others
4. **Development**: Teams can work on different services independently
5. **Resource Optimization**: Each lambda can have appropriate memory/timeout settings
6. **Cost Efficiency**: Pay only for what you use per service

## Monitoring and Debugging

Each lambda function logs its operations and can be monitored independently:
- CloudWatch Logs for each function
- X-Ray tracing for request flow
- Individual function metrics and alarms

## Local Development

To test individual lambdas locally:

```bash
# Build and test orchestrator
cd backend/lambda/orchestrator
docker build -t chatbot-orchestrator .
docker run -p 9000:8080 chatbot-orchestrator

# Test with curl
curl -XPOST "http://localhost:9000/2015-03-31/functions/chatbot-orchestrator/invocations" \
  -d '{"action": "chat", "message": "Hello"}'
```
