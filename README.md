# KnowledgeBot Backend - Unified Architecture

## Overview

This repository contains the backend services for KnowledgeBot, a comprehensive document processing and knowledge management system. The architecture has been redesigned to be more efficient, with clear separation of concerns between document processing and query handling.

## Architecture Changes

### Previous Architecture
- Document upload → Agent → Multiple microservices
- Complex agent orchestration for document processing
- Multiple Docker images for different docling variants

### New Architecture
- **Document Upload**: S3 → Docling Unified Handler (direct trigger)
- **Query Processing**: Agent Query Handler (intelligent routing)
- **Single Docling Image**: Unified processing pipeline

## Service Architecture

### 1. Document Processing Pipeline (S3 Triggered)

**Docling Unified Handler** (`docling-unified-handler.py`)
- **Trigger**: S3 object creation events
- **Process**: 
  - Downloads document from S3
  - Processes with Docling (hierarchical chunking)
  - Generates embeddings using sentence transformers
  - Stores markdown to S3
  - Stores chunks to DynamoDB
  - Stores embeddings to Pinecone
  - Stores relations to Neo4j

**Docker Image**: `Dockerfile.docling-unified`
**Requirements**: `requirements-docling-unified.txt`

### 2. Query Processing Pipeline (API Triggered)

**Intelligent Agent Handler** (`intelligent-agent-handler.py`)
- **Trigger**: HTTP API requests
- **Process**:
  - Analyzes query complexity
  - Decomposes complex queries
  - Routes to appropriate search tools
  - Synthesizes responses from multiple sources
  - Returns comprehensive answers

**Docker Image**: `Dockerfile.intelligent-agent`
**Requirements**: `requirements-intelligent-agent.txt`

### 3. Supporting Microservices

- **Presigned URL Handler**: Generates S3 upload URLs
- **Pinecone Search/Upsert**: Vector similarity operations
- **Neo4j Search/Write**: Graph database operations
- **DynamoDB CRUD**: Document metadata storage
- **S3 Reader**: Document content retrieval
- **Chat Generator**: Response formatting
- **Embedding Generator**: Text-to-vector conversion
- **Text Chunker**: Text segmentation

## Data Flow

### Document Upload Flow
```
1. Client requests presigned URL
2. Client uploads document to S3
3. S3 triggers docling-unified-handler
4. Handler processes document:
   - Extracts content with Docling
   - Generates embeddings
   - Stores to S3 (markdown)
   - Stores to DynamoDB (chunks)
   - Stores to Pinecone (embeddings)
   - Stores to Neo4j (relations)
```

### Query Processing Flow
```
1. Client sends query to intelligent-agent-handler
2. Handler analyzes query complexity
3. Decomposes complex queries if needed
4. Executes searches:
   - Pinecone (vector similarity)
   - Neo4j (graph relationships)
   - DynamoDB (metadata)
   - RAG search (comprehensive)
5. Synthesizes results into coherent response
6. Returns formatted answer with sources
```

## Key Features

### Document Processing
- **Hierarchical Chunking**: Intelligent document structure preservation
- **Multi-format Support**: PDF, DOCX, PPTX, images, text files
- **OCR Capabilities**: Scanned document processing
- **Table Detection**: Structured data extraction
- **Embedding Generation**: Sentence transformer-based vectors

### Query Processing
- **Intelligent Routing**: Automatic tool selection
- **Query Decomposition**: Complex question handling
- **Multi-source Search**: Vector, graph, and metadata search
- **Response Synthesis**: Coherent answer compilation
- **Source Attribution**: Transparent information sources

### Storage Strategy
- **S3**: Raw documents and processed markdown
- **DynamoDB**: Document chunks and metadata
- **Pinecone**: Vector embeddings for similarity search
- **Neo4j**: Document relationships and knowledge graph

## Deployment Process

### GitHub Actions Deployment
The project uses GitHub Actions for automated deployment. The workflow handles:

1. **Pre-build Cleanup**:
   - GitHub Actions cache cleanup
   - ECR image cleanup (keeps last 5 images)
   - Docker layer caching optimization

2. **ECR Repository Management**:
   - Creates repositories if they don't exist
   - Applies lifecycle policies
   - Enables image scanning

3. **Service Building**:
   - Builds Docker images for all services
   - Pushes to ECR with latest tags
   - Validates build success

### Prerequisites for GitHub Actions
- AWS credentials configured in GitHub Secrets
- ECR access permissions
- Lambda deployment permissions

## Environment Variables

### Docling Unified Handler
```bash
DOCUMENTS_BUCKET=chatbot-documents-ap-south-1
PROCESSED_DOCUMENTS_BUCKET=processed-documents
CHUNKS_TABLE=document-chunks
PINECONE_UPSERT_FUNCTION=pinecone-upsert-handler
NEO4J_WRITE_FUNCTION=neo4j-write-handler
```

### Agent Query Handler
```bash
PINECONE_SEARCH_FUNCTION=pinecone-search-handler
NEO4J_SEARCH_FUNCTION=neo4j-search-handler
DYNAMODB_READ_FUNCTION=dynamodb-crud-handler
S3_READER_FUNCTION=s3-reader-handler
```

## Lambda Configuration

### Docling Unified Handler
- **Memory**: 3008 MB (for Docling processing)
- **Timeout**: 15 minutes
- **Trigger**: S3 object creation
- **Environment**: Python 3.12

### Agent Query Handler
- **Memory**: 1024 MB
- **Timeout**: 5 minutes
- **Trigger**: API Gateway
- **Environment**: Python 3.12

## Monitoring and Logging

### CloudWatch Metrics
- Document processing duration
- Query response time
- Error rates by service
- Storage utilization

### Logging Levels
- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: Processing failures
- **DEBUG**: Detailed troubleshooting

## Security Considerations

### IAM Permissions
- S3 read/write access for document buckets
- DynamoDB read/write access for chunks table
- Pinecone API access for vector operations
- Neo4j API access for graph operations
- Lambda invoke permissions for microservices

### Data Privacy
- Documents stored in encrypted S3 buckets
- DynamoDB encryption at rest
- Pinecone data encryption
- No sensitive data in logs

## Troubleshooting

### Common Issues

1. **Document Processing Failures**
   - Check S3 permissions
   - Verify Docling dependencies
   - Monitor Lambda timeout

2. **Query Processing Issues**
   - Check microservice connectivity
   - Verify database permissions
   - Monitor response timeouts

3. **Build Failures**
   - Check ECR authentication
   - Verify Docker daemon
   - Monitor disk space

### Debug Commands
```bash
# Check ECR repositories
aws ecr describe-repositories --region ap-south-1

# Check Lambda function status
aws lambda list-functions --region ap-south-1

# Check CloudWatch logs
aws logs describe-log-groups --region ap-south-1
```

## Performance Optimization

### Document Processing
- Use appropriate Lambda memory allocation
- Implement chunking strategies
- Optimize embedding generation

### Query Processing
- Cache frequent queries
- Optimize search strategies
- Implement response streaming

### Storage
- Use lifecycle policies
- Implement data archiving
- Monitor storage costs

## Future Enhancements

### Planned Features
- Real-time document processing status
- Advanced query understanding
- Multi-language support
- Custom embedding models
- Graph visualization
- Document versioning

### Scalability Improvements
- Horizontal scaling for processing
- Caching layer implementation
- Database optimization
- CDN integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Copyright (c) 2024 Bejoy Pramanick. All rights reserved.
Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
