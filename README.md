# KnowledgeBot Backend - Smart Lambda Segregation Architecture

## Overview

This repository contains the backend services for KnowledgeBot, a comprehensive document processing and knowledge management system. The architecture uses smart segregation between Docker Lambdas (for heavy library installations) and Zip Lambdas (for business logic and CRUD operations).

## 🏗️ Architecture Benefits

✅ **Viewable Business Logic**: All business logic code is visible in AWS Lambda console  
✅ **Efficient Library Management**: Heavy libraries are isolated in Docker containers  
✅ **GitHub-Only Deployment**: All deployments happen through GitHub Actions  
✅ **Comprehensive Logging**: Detailed logging in all business logic functions  
✅ **Clean Separation**: Clear distinction between library installation and business logic  

## 🚀 Lambda Function Structure

### Docker Lambdas (Library Installations Only)

| Function | Purpose | Libraries |
|----------|---------|-----------|
| `docling-library-handler` | Docling library import & init | docling, pypdfium2 |
| `pinecone-library-handler` | Pinecone library import & init | pinecone-client |
| `neo4j-library-handler` | Neo4j library import & init | neo4j |
| `openai-library-handler` | OpenAI library import & init | openai |
| `sentence-transformer-library-handler` | Sentence Transformer import & init | sentence-transformers, torch |

### Zip Lambdas (Business Logic & CRUD)

| Function | Purpose | Business Logic |
|----------|---------|----------------|
| `document-processor-business-logic` | Document processing pipeline | S3 download, Docling calls, DynamoDB storage, Pinecone upsert, Neo4j relations |
| `chat-orchestrator-business-logic` | Chat and query processing | RAG search, vector similarity, graph queries, OpenAI generation |
| `dynamodb-crud-handler` | DynamoDB operations | CRUD operations, batch operations, queries |
| `s3-unified-handler` | S3 operations | Upload, download, list, presigned URLs |

## 📁 File Structure

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

## 🔄 Business Logic Flow

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

## 🚀 Deployment

All deployment happens through GitHub Actions:

- **Push to main** → Triggers automatic deployment
- **Docker Lambdas** → Built and deployed first
- **Zip Lambdas** → Built and deployed second
- **Environment Variables** → Automatically configured

## 📊 Logging

All business logic functions include comprehensive logging:

```python
logger.info(f"🚀 Starting document processing pipeline for: {filename}")
logger.info(f"🔧 Calling Docling library for document: {filename}")
logger.info(f"✅ Docling library processed successfully: {chunks} chunks")
logger.error(f"❌ Error calling Docling library: {e}")
```

## 🎯 Key Benefits

1. **Visibility**: All business logic is viewable in AWS Lambda console
2. **Maintainability**: Clear separation between library installation and business logic
3. **Efficiency**: Heavy libraries are pre-installed in Docker containers
4. **Scalability**: Business logic can be easily modified without rebuilding Docker images
5. **Debugging**: Comprehensive logging makes troubleshooting easier
6. **GitHub Integration**: All deployments happen through GitHub Actions
7. **Cost Optimization**: Zip Lambdas are faster to deploy and cheaper to run

## 📚 Documentation

- **`ARCHITECTURE-SMART-SEGREGATION.md`** - Detailed architecture documentation
- **`REQUIREMENTS-SUMMARY.md`** - Requirements files explanation

## 🔧 Getting Started

1. **Push to GitHub**: All changes trigger automatic deployment
2. **View Business Logic**: Check AWS Lambda console for all business logic code
3. **Monitor Logs**: Use CloudWatch logs to see detailed execution flow
4. **Modify Logic**: Edit business logic files and push to GitHub for automatic deployment

---

**This architecture provides the perfect balance between heavy library management (Docker Lambdas) and readable business logic (Zip Lambdas) with GitHub-based deployment.**