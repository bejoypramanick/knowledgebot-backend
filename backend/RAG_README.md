# RAG-Powered Chatbot with Docling Processing

This is a complete RAG (Retrieval-Augmented Generation) system that processes documents using Docling for semantic hierarchical chunking and creates embeddings for intelligent document search and chat.

## 🏗️ Architecture

### Components

1. **RAG Processor Lambda** (`chatbot-rag-processor`)
   - Containerized Lambda function
   - Processes documents using Docling
   - Creates semantic hierarchical chunks
   - Generates embeddings using Claude API
   - Stores chunks in DynamoDB and embeddings in S3

2. **Chat Handler Lambda** (`chatbot-chat-handler`)
   - Containerized Lambda function
   - Handles chat conversations
   - Uses RAG for context retrieval
   - Generates responses using Claude API
   - Manages conversation history

3. **S3 Event Trigger**
   - Automatically processes new document uploads
   - Triggers RAG processor when documents are uploaded

4. **Storage**
   - **S3 Buckets**: Documents and embeddings storage
   - **DynamoDB Tables**: Knowledge base chunks and conversation history

## 🚀 Quick Start

### 1. Setup AWS Resources

```bash
cd backend
./setup-aws-resources.sh
```

This creates:
- S3 buckets for documents and embeddings
- DynamoDB tables for knowledge base and conversations
- IAM roles and policies
- ECR repositories for container images

### 2. Deploy Lambda Functions

Push your code to GitHub. The GitHub Actions workflow will:
- Build container images for both Lambda functions
- Push images to ECR
- Deploy Lambda functions
- Configure S3 event triggers
- Set environment variables

### 3. Update Frontend

Update your frontend to use the new API endpoints:
- `/chat` - For chat conversations
- `/knowledge-base` - For document management

## 📁 Project Structure

```
backend/
├── lambda/
│   ├── rag-processor/          # RAG processing Lambda
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── rag_processor.py
│   ├── chat-handler/           # Chat handling Lambda
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── chat_handler.py
│   └── [deprecated files]      # Old Lambda functions
├── .github/workflows/
│   └── deploy-lambda-containers.yml
├── setup-aws-resources.sh
└── RAG_README.md
```

## 🔧 Features

### Document Processing
- **OCR Support**: Automatic text extraction from images and PDFs
- **Hierarchical Chunking**: Creates semantic document structure
- **Multiple Formats**: PDF, DOCX, images, and more
- **Metadata Extraction**: Preserves document metadata

### RAG System
- **Docling RAG Search**: Uses Docling's built-in RAG capabilities for document search
- **Direct Document Search**: Searches documents directly using Docling's semantic understanding
- **Context Retrieval**: Finds relevant chunks using Docling's RAG search
- **Hierarchical Context**: Uses document structure for better context
- **Claude Integration**: Uses Claude API for response generation

### Chat System
- **Conversation History**: Maintains chat context
- **RAG-Enhanced Responses**: Uses knowledge base for accurate answers
- **Source Citation**: References document sources in responses

## 🛠️ Configuration

### Environment Variables

**RAG Processor Lambda:**
- `DOCUMENTS_BUCKET`: S3 bucket for documents
- `EMBEDDINGS_BUCKET`: S3 bucket for embeddings
- `KNOWLEDGE_BASE_TABLE`: DynamoDB table for chunks
- `CLAUDE_API_KEY`: Anthropic Claude API key

**Chat Handler Lambda:**
- `DOCUMENTS_BUCKET`: S3 bucket for documents
- `EMBEDDINGS_BUCKET`: S3 bucket for embeddings
- `KNOWLEDGE_BASE_TABLE`: DynamoDB table for chunks
- `CONVERSATIONS_TABLE`: DynamoDB table for conversations
- `CLAUDE_API_KEY`: Anthropic Claude API key
- `RAG_PROCESSOR_LAMBDA`: Name of RAG processor Lambda

### GitHub Secrets

Add these secrets to your GitHub repository:
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `CLAUDE_API_KEY`: Anthropic Claude API key

## 📊 API Endpoints

### Chat Endpoint (`/chat`)

**POST** `/chat`
```json
{
  "action": "chat",
  "message": "What is the return policy?",
  "conversation_id": "optional-conversation-id",
  "use_rag": true
}
```

**Response:**
```json
{
  "response": "Based on our knowledge base...",
  "conversation_id": "conversation-id",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Document Upload (`/chat`)

**POST** `/chat`
```json
{
  "action": "get-upload-url",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "metadata": {
    "title": "Document Title",
    "category": "general",
    "author": "Author Name"
  }
}
```

**Response:**
```json
{
  "presigned_url": "https://s3...",
  "document_id": "uuid",
  "s3_key": "documents/uuid/document.pdf",
  "bucket": "chatbot-documents-ap-south-1",
  "metadata": {...}
}
```

### Document Listing (`/knowledge-base`)

**POST** `/knowledge-base`
```json
{
  "action": "list"
}
```

**Response:**
```json
{
  "documents": [
    {
      "document_id": "uuid",
      "filename": "document.pdf",
      "title": "Document Title",
      "upload_timestamp": "2024-01-01T00:00:00Z",
      "category": "general",
      "author": "Author Name"
    }
  ],
  "count": 1
}
```

## 🔍 How It Works

### Document Upload Flow
1. Frontend requests presigned URL from Chat Handler
2. Document is uploaded directly to S3
3. S3 event triggers RAG Processor Lambda
4. RAG Processor processes document with Docling
5. Creates hierarchical chunks (no embeddings needed)
6. Stores chunks in DynamoDB for reference

### Chat Flow
1. User sends message to API Gateway
2. API Gateway calls RAG Processor Lambda directly
3. RAG Processor uses Docling's RAG search on documents
4. Retrieves relevant chunks using Docling's semantic understanding
5. Returns results to Chat Handler
6. Chat Handler generates response using Claude with retrieved context
7. Saves conversation history to DynamoDB

## 🐳 Container Images

### RAG Processor
- **Base**: `public.ecr.aws/lambda/python:3.9`
- **Dependencies**: Docling, Pydantic, Anthropic, boto3
- **Features**: OCR, document processing, Docling RAG search

### Chat Handler
- **Base**: `public.ecr.aws/lambda/python:3.9`
- **Dependencies**: Anthropic, boto3, Pydantic
- **Features**: Chat management, RAG integration, conversation history

## 📈 Monitoring

### CloudWatch Logs
- `/aws/lambda/chatbot-rag-processor`
- `/aws/lambda/chatbot-chat-handler`

### Metrics
- Lambda invocations and errors
- S3 object uploads
- DynamoDB read/write capacity

## 🔧 Troubleshooting

### Common Issues

1. **Document not processing**
   - Check S3 event trigger configuration
   - Verify RAG Processor Lambda permissions
   - Check CloudWatch logs

2. **Chat responses not using RAG**
   - Verify RAG Processor Lambda is accessible
   - Check knowledge base has data
   - Verify Claude API key

3. **Container build failures**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt
   - Check ECR repository permissions

### Debug Commands

```bash
# Check Lambda function status
aws lambda get-function --function-name chatbot-rag-processor --region ap-south-1

# Check S3 event configuration
aws s3api get-bucket-notification-configuration --bucket chatbot-documents-ap-south-1

# Check DynamoDB tables
aws dynamodb describe-table --table-name chatbot-knowledge-base --region ap-south-1
```

## 🚀 Deployment

1. **Setup AWS Resources**: Run `./setup-aws-resources.sh`
2. **Push to GitHub**: Triggers automatic deployment
3. **Monitor Deployment**: Check GitHub Actions logs
4. **Test Functionality**: Upload documents and test chat

## 📝 Notes

- All old Lambda functions are deprecated and return 410 status
- Use containerized Lambda functions for new deployments
- S3 CORS is configured for localhost development
- DynamoDB uses on-demand billing for cost efficiency
- ECR repositories have lifecycle policies to manage image storage
