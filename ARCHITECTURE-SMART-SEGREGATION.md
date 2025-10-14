# KnowledgeBot Backend - Smart Lambda Segregation Architecture

## Overview

This architecture smartly segregates Lambda functions into two categories:
- **Docker Lambdas**: ONLY for heavy library installations (docling, pinecone, neo4j, openai, etc.)
- **Zip Lambdas**: ALL business logic and CRUD operations (viewable in AWS Lambda console)

## Architecture Benefits

✅ **Viewable Business Logic**: All your business logic code is visible in AWS Lambda console  
✅ **Efficient Library Management**: Heavy libraries are isolated in Docker containers  
✅ **GitHub-Only Deployment**: All deployments happen through GitHub Actions  
✅ **Comprehensive Logging**: Detailed logging in all business logic functions  
✅ **Clean Separation**: Clear distinction between library installation and business logic  

## Lambda Function Structure

### Docker Lambdas (Library Installations Only)

| Function | Purpose | Dockerfile | Libraries |
|----------|---------|------------|-----------|
| `docling-library-handler` | Docling library import & init | `Dockerfile.docling-library` | docling, pypdfium2 |
| `pinecone-library-handler` | Pinecone library import & init | `Dockerfile.pinecone-library` | pinecone-client |
| `neo4j-library-handler` | Neo4j library import & init | `Dockerfile.neo4j-library` | neo4j |
| `openai-library-handler` | OpenAI library import & init | `Dockerfile.openai-library` | openai |
| `sentence-transformer-library-handler` | Sentence Transformer import & init | `Dockerfile.sentence-transformer-library` | sentence-transformers, torch |

**Key Points:**
- These functions ONLY import and initialize libraries
- No business logic or CRUD operations
- Return success/failure status only
- Heavy dependencies are pre-installed in Docker images

### Zip Lambdas (Business Logic & CRUD)

| Function | Purpose | Business Logic |
|----------|---------|----------------|
| `document-processor-business-logic` | Document processing pipeline | S3 download, Docling calls, DynamoDB storage, Pinecone upsert, Neo4j relations |
| `chat-orchestrator-business-logic` | Chat and query processing | RAG search, vector similarity, graph queries, OpenAI generation |
| `dynamodb-crud-handler` | DynamoDB operations | CRUD operations, batch operations, queries |
| `s3-unified-handler` | S3 operations | Upload, download, list, presigned URLs |

**Key Points:**
- ALL business logic and CRUD operations
- Comprehensive logging with emojis and detailed messages
- Call Docker Lambdas for heavy library operations
- Viewable in AWS Lambda console

## File Structure

```
microservices/
├── # Docker Lambda Handlers (Library Only)
├── docling-library-handler.py          # Docling import & init
├── pinecone-library-handler.py         # Pinecone import & init
├── neo4j-library-handler.py            # Neo4j import & init
├── openai-library-handler.py           # OpenAI import & init
├── sentence-transformer-library-handler.py # Sentence Transformer import & init
│
├── # Zip Lambda Handlers (Business Logic)
├── document-processor-business-logic.py # Document processing pipeline
├── chat-orchestrator-business-logic.py # Chat orchestration
├── dynamodb-crud-handler.py            # DynamoDB CRUD
└── s3-unified-handler.py               # S3 operations

# Dockerfiles for Library Handlers
Dockerfile.docling-library
Dockerfile.pinecone-library
Dockerfile.neo4j-library
Dockerfile.openai-library
Dockerfile.sentence-transformer-library

# Requirements
requirements-docker-lambdas.txt         # Heavy library dependencies
requirements-zip-lambdas.txt            # Minimal business logic dependencies

# GitHub Actions
.github/workflows/
├── deploy-docker-lambdas.yml           # Deploy Docker Lambdas
├── deploy-zip-lambdas.yml              # Deploy Zip Lambdas
└── deploy-all-lambdas.yml              # Deploy everything
```

## Deployment Process

### 1. GitHub Actions Workflows

**Docker Lambdas Deployment** (`.github/workflows/deploy-docker-lambdas.yml`):
- Triggers on changes to library handlers or Dockerfiles
- Builds Docker images for each library handler
- Pushes to ECR
- Deploys Lambda functions
- Cleans up old images

**Zip Lambdas Deployment** (`.github/workflows/deploy-zip-lambdas.yml`):
- Triggers on changes to business logic handlers
- Creates zip packages with minimal dependencies
- Deploys Lambda functions
- Sets environment variables for library function names

**All Lambdas Deployment** (`.github/workflows/deploy-all-lambdas.yml`):
- Orchestrates both deployments
- Deploys Docker Lambdas first, then Zip Lambdas
- Provides deployment summary

### 2. Environment Variables

Business logic functions are configured with environment variables to know which library functions to call:

```bash
DOCLING_LIBRARY_FUNCTION=docling-library-handler
PINECONE_LIBRARY_FUNCTION=pinecone-library-handler
NEO4J_LIBRARY_FUNCTION=neo4j-library-handler
OPENAI_LIBRARY_FUNCTION=openai-library-handler
SENTENCE_TRANSFORMER_LIBRARY_FUNCTION=sentence-transformer-library-handler
CHUNKS_TABLE=document-chunks
PROCESSED_DOCUMENTS_BUCKET=processed-documents
```

## Business Logic Flow

### Document Processing Pipeline

1. **S3 Event** → `document-processor-business-logic`
2. **Download** document from S3
3. **Call** `docling-library-handler` for document processing
4. **Store** markdown to S3
5. **Call** `sentence-transformer-library-handler` for embeddings
6. **Store** chunks to DynamoDB
7. **Call** `pinecone-library-handler` for vector storage
8. **Call** `neo4j-library-handler` for graph relations

### Chat Processing Pipeline

1. **API Request** → `chat-orchestrator-business-logic`
2. **Call** `sentence-transformer-library-handler` for query embedding
3. **Call** `pinecone-library-handler` for vector search
4. **Call** `neo4j-library-handler` for graph queries
5. **Search** DynamoDB for additional context
6. **Call** `openai-library-handler` for response generation
7. **Return** comprehensive response

## Logging Strategy

All business logic functions include comprehensive logging:

```python
logger.info(f"🚀 Starting document processing pipeline for: {filename}")
logger.info(f"🔧 Calling Docling library for document: {filename}")
logger.info(f"✅ Docling library processed successfully: {chunks} chunks")
logger.error(f"❌ Error calling Docling library: {e}")
```

## Benefits of This Architecture

1. **Visibility**: All business logic is viewable in AWS Lambda console
2. **Maintainability**: Clear separation between library installation and business logic
3. **Efficiency**: Heavy libraries are pre-installed in Docker containers
4. **Scalability**: Business logic can be easily modified without rebuilding Docker images
5. **Debugging**: Comprehensive logging makes troubleshooting easier
6. **GitHub Integration**: All deployments happen through GitHub Actions
7. **Cost Optimization**: Zip Lambdas are faster to deploy and cheaper to run

## Getting Started

1. **Push to GitHub**: All changes trigger automatic deployment
2. **View Business Logic**: Check AWS Lambda console for all business logic code
3. **Monitor Logs**: Use CloudWatch logs to see detailed execution flow
4. **Modify Logic**: Edit business logic files and push to GitHub for automatic deployment

## Summary

This architecture provides the perfect balance between:
- **Heavy library management** (Docker Lambdas)
- **Readable business logic** (Zip Lambdas)
- **GitHub-based deployment** (No local scripts)
- **Comprehensive logging** (Full visibility)

All your business logic and CRUD operations are now viewable in the AWS Lambda console, while heavy library installations are efficiently managed through Docker containers.
