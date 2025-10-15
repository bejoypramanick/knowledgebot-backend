# GitHub Secrets Quick Reference

## Required Secrets for MCP Server Deployment

### AWS Configuration
```
AWS_ACCOUNT_ID
AWS_ACCESS_KEY_ID  
AWS_SECRET_ACCESS_KEY
```

### Docling MCP Server
```
DOCLING_MCP_SERVER_TIMEOUT
```

### Neo4j MCP Server
```
NEO4J_MCP_SERVER_TIMEOUT
NEO4J_URI
NEO4J_USER
NEO4J_PASSWORD
```

### Pinecone MCP Server
```
PINECONE_MCP_SERVER_TIMEOUT
PINECONE_API_KEY
PINECONE_ENVIRONMENT
PINECONE_INDEX_NAME
```

### DynamoDB MCP Server
```
DYNAMODB_MCP_SERVER_TIMEOUT
```

## Setup Instructions

1. Go to GitHub Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with the exact name above
4. Set appropriate values for your environment

## Total Secrets Required: 11

- 3 AWS secrets
- 1 Docling MCP secret (URL is auto-generated)
- 4 Neo4j MCP secrets (URL is auto-generated)
- 4 Pinecone MCP secrets (URL is auto-generated)
- 1 DynamoDB MCP secret (URL is auto-generated)

**Note**: MCP server URLs are automatically generated as Lambda function URLs during deployment.

See `GITHUB_SECRETS_SETUP.md` for detailed configuration examples.
