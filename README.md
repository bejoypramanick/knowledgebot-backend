# KnowledgeBot Backend

A production-ready RAG (Retrieval-Augmented Generation) backend system with advanced document processing capabilities using Docling, Pinecone vector database, Neo4j graph database, and AWS Lambda.

## ⚠️ IMPORTANT - LICENSE AND USAGE RESTRICTIONS

**This software is proprietary and confidential to Bejoy Pramanick and Globistaan.**

### Commercial Use Prohibited
- **NO COMMERCIAL USE** without explicit written permission
- This includes selling, licensing, monetizing, or incorporating into commercial products
- Violation may result in legal action

### Permitted Use
- Personal, educational, and non-commercial use only
- Source code may be viewed for learning purposes
- Contributions must be submitted back to the original author

### Licensing Inquiries
For commercial licensing, contact: **bejoy.pramanick@globistaan.com**

## Features

### 🚀 Core Capabilities
- **Multi-Modal Document Processing**: PDF, DOCX, TXT, HTML, Markdown support
- **Hierarchical Semantic Chunking**: Advanced document structure analysis
- **Vector Search**: Pinecone integration for semantic similarity
- **Graph Database**: Neo4j for knowledge relationships
- **AI Agent**: GPT-4 powered query decomposition and response generation
- **AWS Integration**: Lambda, S3, DynamoDB, ECR

### 🏗️ Architecture
- **Parallel Docker Builds**: Separate images for different components
- **Microservices**: Modular Lambda functions
- **Production-Ready**: Comprehensive error handling and logging
- **Scalable**: Auto-scaling AWS Lambda functions

## Docker Images

### 1. Core Dependencies (`Dockerfile.core`)
- Basic ML stack (PyTorch, Transformers, Sentence Transformers)
- AWS SDK and database clients
- Optimized for chat functionality

### 2. Docling Processing (`Dockerfile.docling`)
- Advanced document processing with Docling
- Hierarchical semantic chunking
- Document ingestion pipeline

### 3. Final Application (`Dockerfile.final`)
- Complete application with all dependencies
- Production-ready deployment
- All features integrated

## Environment Variables

### Required AWS Configuration
```bash
AWS_REGION=ap-south-1
S3_BUCKET=chatbot-storage-ap-south-1
DYNAMODB_TABLE=chatbot-knowledge-base-metadata
KNOWLEDGE_BASE_TABLE=chatbot-knowledge-base
CONVERSATIONS_TABLE=chatbot-conversations
DOCUMENTS_BUCKET=chatbot-documents-ap-south-1
EMBEDDINGS_BUCKET=chatbot-embeddings-ap-south-1
```

### Pinecone Configuration
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_index_name
PINECONE_HOST=your_pinecone_host
PINECONE_DIMENSIONS=384
PINECONE_METRIC=cosine
```

### Neo4j Configuration
```bash
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USERNAME=your_username
NEO4J_PASSWORD=your_password
```

### OpenAI Configuration
```bash
OPENAI_API_KEY=your_openai_api_key
```

### Embedding Configuration
```bash
EMBEDDING_TYPE=local  # or 'openai'
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Deployment

### GitHub Actions Workflow
The project uses parallel Docker builds for efficiency:

1. **Setup Infrastructure**: Creates ECR repositories
2. **Build Core**: Core dependencies image (parallel)
3. **Build Docling**: Document processing image (parallel)
4. **Build Final**: Complete application image (parallel)
5. **Deploy**: Deploy to AWS Lambda

### Manual Deployment
```bash
# Build images
docker build -f Dockerfile.core -t knowledgebot-core .
docker build -f Dockerfile.docling -t knowledgebot-docling .
docker build -f Dockerfile.final -t knowledgebot-final .

# Push to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.ap-south-1.amazonaws.com
docker tag knowledgebot-core:latest your-account.dkr.ecr.ap-south-1.amazonaws.com/knowledgebot-backend-core:latest
docker push your-account.dkr.ecr.ap-south-1.amazonaws.com/knowledgebot-backend-core:latest
```

## API Endpoints

### Chat Endpoint
- **Function**: `knowledgebot-chat`
- **Purpose**: Handle user queries and generate responses
- **Features**: Query decomposition, RAG search, response generation

### Document Ingestion
- **Function**: `knowledgebot-document-ingestion`
- **Purpose**: Process and ingest documents
- **Features**: Docling processing, hierarchical chunking, vector storage

## Technology Stack

- **Language**: Python 3.11
- **ML/AI**: PyTorch, Transformers, Sentence Transformers, OpenAI GPT-4
- **Document Processing**: Docling
- **Vector Database**: Pinecone
- **Graph Database**: Neo4j
- **Cloud**: AWS (Lambda, S3, DynamoDB, ECR)
- **Containerization**: Docker
- **CI/CD**: GitHub Actions

## Security & Compliance

- **Proprietary Code**: All rights reserved
- **Commercial Use**: Requires explicit permission
- **Data Protection**: Environment variables for sensitive data
- **Access Control**: AWS IAM integration

## Support

For technical support or commercial licensing inquiries:
- **Email**: bejoy.pramanick@globistaan.com
- **Company**: Globistaan

---

**© 2024 Bejoy Pramanick. All rights reserved.**# Trigger build
# Force build trigger - Thu Oct  9 16:41:05 CEST 2025
# Fresh build trigger - Thu Oct  9 17:02:37 CEST 2025
