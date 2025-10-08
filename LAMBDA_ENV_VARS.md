# Lambda Environment Variables Configuration

This document lists all required environment variables for the Lambda deployment.

## Required Environment Variables

### Pinecone Configuration
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=chatbot-embeddings
PINECONE_HOST=https://chatbot-embeddings-ogo9re7.svc.aped-4627-b74a.pinecone.io
PINECONE_DIMENSIONS=1536
PINECONE_METRIC=cosine
```

### AWS Configuration
```bash
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

### Neo4j Configuration
```bash
NEO4J_URI=your_neo4j_uri
NEO4J_USER=your_neo4j_username
NEO4J_PASSWORD=your_neo4j_password
```

### Embedding Configuration (Optional - defaults to sentence transformers)
```bash
EMBEDDING_TYPE=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Optional: OpenAI Configuration (if using OpenAI embeddings)
```bash
OPENAI_API_KEY=your_openai_api_key
```

## Docker Environment Variables

The Dockerfile sets these default values that can be overridden by Lambda environment variables:

```dockerfile
ENV EMBEDDING_TYPE=local
ENV EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Deployment Notes

1. All Pinecone variables are required and must match your index configuration
2. AWS credentials are required for S3 and DynamoDB access
3. Neo4j credentials are required for graph database operations
4. The system defaults to sentence transformers for embeddings (no API costs)
5. Set `EMBEDDING_TYPE=openai` and provide `OPENAI_API_KEY` to use OpenAI embeddings instead
