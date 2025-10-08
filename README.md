# KnowledgeBot Backend

A production-ready RAG (Retrieval-Augmented Generation) system with multi-stage Docker builds for efficient deployment.

## Architecture

- **Pinecone**: Vector database for semantic search
- **Neo4j**: Graph database for knowledge relationships  
- **DynamoDB**: Metadata storage
- **S3**: Document storage
- **GPT-4**: Query decomposition and response generation
- **Sentence Transformers**: Local embeddings (no API costs)

## Multi-Stage Build

The system uses 6 optimized build stages:

1. **Setup Infrastructure** - AWS resources
2. **Core Dependencies** - Essential Python packages (~2-3GB)
3. **Document Processing** - Docling, OpenCV, PDF tools (~4-5GB)
4. **NLP Processing** - spaCy, NLTK, Redis (~3-4GB)
5. **Final Application** - Application code only (~2.5GB)
6. **Deploy Lambda** - Lambda function deployment

## Features

- ✅ **Query Decomposition**: GPT-4 breaks complex queries into sub-questions
- ✅ **Multi-Part Responses**: Structured answers for multiple questions
- ✅ **Knowledge Graphs**: Neo4j relationships enhance context
- ✅ **Vector Search**: Pinecone semantic similarity
- ✅ **Local Embeddings**: Sentence transformers (no API costs)
- ✅ **Production Ready**: Optimized for AWS Lambda

## Environment Variables

Required secrets in GitHub "chatbot" environment:

```
PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME
PINECONE_HOST, PINECONE_DIMENSIONS, PINECONE_METRIC
NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
```

## Deployment

The system automatically deploys via GitHub Actions when code is pushed to main branch.

## Project Structure

```
agent-toolkit/
├── crud_operations.py      # Core data operations
├── lambda_handlers.py      # AWS Lambda handlers
├── rag_agent.py           # GPT-4 agent with tools
├── rag_operations.py      # RAG pipeline operations
└── requirements.txt       # Python dependencies
```
