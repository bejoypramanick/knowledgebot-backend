# GitHub Actions Environment Variables

This document lists all the environment variables that need to be configured in GitHub Secrets for successful deployment.

## Required GitHub Secrets

### AWS Credentials
- `AWS_ACCESS_KEY_ID` - AWS access key for deployment
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for deployment
- `AWS_ACCOUNT_ID` - AWS account ID for ECR and IAM roles

### MCP Server URLs and Timeouts
- `DOCLING_MCP_SERVER_URL` - URL of the Docling MCP server
- `DOCLING_MCP_SERVER_TIMEOUT` - Timeout for Docling MCP server (default: 30)
- `NEO4J_MCP_SERVER_URL` - URL of the Neo4j MCP server
- `NEO4J_MCP_SERVER_TIMEOUT` - Timeout for Neo4j MCP server (default: 30)
- `PINECONE_MCP_SERVER_URL` - URL of the Pinecone MCP server (auto-generated)
- `PINECONE_MCP_SERVER_TIMEOUT` - Timeout for Pinecone MCP server (default: 30)
- `DYNAMODB_MCP_SERVER_URL` - URL of the DynamoDB MCP server (auto-generated)
- `DYNAMODB_MCP_SERVER_TIMEOUT` - Timeout for DynamoDB MCP server (default: 30)

### Database Credentials
- `NEO4J_URI` - Neo4j database URI
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password

### Pinecone Configuration
- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_ENVIRONMENT` - Pinecone environment (e.g., us-east-1-aws)
- `PINECONE_INDEX_NAME` - Pinecone index name
- `PINECONE_EMBEDDING_MODEL` - Pinecone embedding model (e.g., nvidia/llama-text-embed-v2)
- `PINECONE_EMBEDDING_DIMENSIONS` - Embedding dimensions (e.g., 1024)

### OpenAI Configuration
- `OPENAI_API_KEY` - OpenAI API key

### S3 Configuration
- `DOCUMENTS_BUCKET` - S3 bucket for uploaded documents (auto-created as `knowledgebot-documents-{environment}`)
- `PROCESSED_DOCUMENTS_BUCKET` - S3 bucket for processed documents (auto-created as `processed-documents-{environment}`)

### DynamoDB Configuration
- `CHUNKS_TABLE` - DynamoDB table for document chunks (auto-created as `document-chunks-{environment}`)
- `ERROR_LOGS_TABLE` - DynamoDB table for error logs (auto-created as `knowledgebot-error-logs-{environment}`)

## Environment Variables Set by GitHub Actions

The following environment variables are automatically set by the GitHub Actions workflow:

- `AWS_REGION` - Set to `ap-south-1`
- `ECR_REGISTRY` - Set to `{AWS_ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com`
- `PINECONE_MCP_SERVER_URL` - Auto-generated from Lambda function URL
- `DYNAMODB_MCP_SERVER_URL` - Auto-generated from Lambda function URL

## Lambda Function Environment Variables

The following environment variables are set on Lambda functions during deployment:

### Chat Orchestrator WebSocket
- `SENTENCE_TRANSFORMER_LIBRARY_FUNCTION` - Reference to SentenceTransformer function
- `OPENAI_LIBRARY_FUNCTION` - Reference to OpenAI function
- `DOCLING_MCP_SERVER_FUNCTION` - Reference to Docling MCP function
- `PINECONE_MCP_SERVER_FUNCTION` - Reference to Pinecone MCP function
- `NEO4J_MCP_SERVER_FUNCTION` - Reference to Neo4j MCP function
- `DYNAMODB_MCP_FUNCTION` - Reference to DynamoDB MCP function
- `OPENAI_AGENTS_FUNCTION` - Reference to OpenAI Agents function

### Document Processor
- `DOCUMENTS_BUCKET` - S3 bucket for documents
- `PROCESSED_DOCUMENTS_BUCKET` - S3 bucket for processed documents
- `CHUNKS_TABLE` - DynamoDB table for chunks
- `DOCLING_LIBRARY_FUNCTION` - Reference to Docling function
- `PINECONE_LIBRARY_FUNCTION` - Reference to Pinecone function
- `NEO4J_LIBRARY_FUNCTION` - Reference to Neo4j function
- `DYNAMODB_MCP_FUNCTION` - Reference to DynamoDB MCP function

### MCP Servers
Each MCP server gets its specific configuration:
- Docling: `DOCLING_MCP_SERVER_URL`, `DOCLING_MCP_SERVER_TIMEOUT`
- Neo4j: `NEO4J_MCP_SERVER_URL`, `NEO4J_MCP_SERVER_TIMEOUT`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Pinecone: `PINECONE_MCP_SERVER_URL`, `PINECONE_MCP_SERVER_TIMEOUT`, `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, `PINECONE_INDEX_NAME`
- DynamoDB: `DYNAMODB_MCP_SERVER_URL`, `DYNAMODB_MCP_SERVER_TIMEOUT`, `AWS_REGION`

## Setup Instructions

1. Go to your GitHub repository
2. Navigate to Settings > Secrets and variables > Actions
3. Add each of the required secrets listed above
4. Ensure all values are correct and up-to-date
5. The deployment will automatically use these secrets during the GitHub Actions workflow

## Notes

- Some URLs (like MCP server URLs) are auto-generated during deployment
- The workflow will create Lambda function URLs for MCP servers automatically
- All sensitive information should be stored as GitHub Secrets, not in the code
- The `AWS_REGION` is hardcoded to `ap-south-1` in the workflow
