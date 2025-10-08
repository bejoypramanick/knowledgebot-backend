# Pinecone Configuration

Based on the chatbot-embeddings index configuration, here are the required environment variables:

## Pinecone Settings (All Required)
```bash
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=chatbot-embeddings
PINECONE_HOST=https://chatbot-embeddings-ogo9re7.svc.aped-4627-b74a.pinecone.io
PINECONE_DIMENSIONS=1536
PINECONE_METRIC=cosine
```

**Note**: All Pinecone environment variables are now actively used in the code:
- `PINECONE_HOST` - Used for connection validation and logging
- `PINECONE_DIMENSIONS` - Used for embedding dimension validation
- `PINECONE_METRIC` - Used for configuration tracking
- `PINECONE_API_KEY` - Used for authentication
- `PINECONE_ENVIRONMENT` - Used for region configuration
- `PINECONE_INDEX_NAME` - Used for index selection

## Index Details
- **Index Name**: chatbot-embeddings
- **Host**: https://chatbot-embeddings-ogo9re7.svc.aped-4627-b74a.pinecone.io
- **Region**: us-east-1
- **Dimensions**: 1536
- **Metric**: cosine
- **Type**: Dense
- **Capacity Mode**: Serverless
- **Cloud**: AWS

## Embedding Configuration
The system is now configured to use sentence transformers by default:
```bash
EMBEDDING_TYPE=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Other Required Environment Variables
```bash
# AWS Configuration
AWS_REGION=ap-south-1

# Neo4j Configuration
NEO4J_URI=your_neo4j_uri_here
NEO4J_USER=your_neo4j_username_here
NEO4J_PASSWORD=your_neo4j_password_here

# Optional: OpenAI Configuration (if using OpenAI embeddings)
OPENAI_API_KEY=your_openai_api_key_here
```
