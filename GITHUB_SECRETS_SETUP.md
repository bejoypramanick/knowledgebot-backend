# GitHub Secrets Setup for KnowledgeBot Backend

This document lists all the required GitHub secrets that need to be configured in your repository for the MCP server deployment to work properly.

## Required GitHub Secrets

### AWS Configuration
- `AWS_ACCOUNT_ID` - Your AWS Account ID (e.g., `123456789012`)
- `AWS_ACCESS_KEY_ID` - AWS Access Key ID for GitHub Actions
- `AWS_SECRET_ACCESS_KEY` - AWS Secret Access Key for GitHub Actions

### Docling MCP Server Configuration
- `DOCLING_MCP_SERVER_URL` - URL of the Docling MCP server (e.g., `http://docling-mcp-server:5001`)
- `DOCLING_MCP_SERVER_TIMEOUT` - Timeout in seconds for Docling MCP requests (e.g., `300`)

### Neo4j MCP Server Configuration
- `NEO4J_MCP_SERVER_URL` - URL of the Neo4j MCP server (e.g., `http://neo4j-mcp-server:3000`)
- `NEO4J_MCP_SERVER_TIMEOUT` - Timeout in seconds for Neo4j MCP requests (e.g., `300`)
- `NEO4J_URI` - Neo4j database URI (e.g., `bolt://neo4j:7687`)
- `NEO4J_USER` - Neo4j username (e.g., `neo4j`)
- `NEO4J_PASSWORD` - Neo4j password (e.g., `your-secure-password`)

### Pinecone MCP Server Configuration
- `PINECONE_MCP_SERVER_TIMEOUT` - Timeout in seconds for Pinecone MCP requests (e.g., `300`)
- `PINECONE_API_KEY` - Your Pinecone API key
- `PINECONE_ENVIRONMENT` - Pinecone environment (e.g., `us-west1-gcp-free`)
- `PINECONE_INDEX_NAME` - Name of your Pinecone index (e.g., `knowledgebot-index`)

### DynamoDB MCP Server Configuration
- `DYNAMODB_MCP_SERVER_TIMEOUT` - Timeout in seconds for DynamoDB MCP requests (e.g., `300`)

## How to Set Up GitHub Secrets

1. **Go to your GitHub repository**
2. **Click on "Settings" tab**
3. **Click on "Secrets and variables" in the left sidebar**
4. **Click on "Actions"**
5. **Click "New repository secret"**
6. **Add each secret with the exact name and value**

## Example Secret Values

### For Development/Testing
```bash
# AWS Configuration
AWS_ACCOUNT_ID=123456789012
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Docling MCP Server
DOCLING_MCP_SERVER_URL=http://docling-mcp-server:5001
DOCLING_MCP_SERVER_TIMEOUT=300

# Neo4j MCP Server
NEO4J_MCP_SERVER_URL=http://neo4j-mcp-server:3000
NEO4J_MCP_SERVER_TIMEOUT=300
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# Pinecone MCP Server
PINECONE_MCP_SERVER_URL=http://pinecone-mcp-server:3000
PINECONE_MCP_SERVER_TIMEOUT=300
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp-free
PINECONE_INDEX_NAME=knowledgebot-index
```

### For Production
```bash
# AWS Configuration
AWS_ACCOUNT_ID=123456789012
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Docling MCP Server
DOCLING_MCP_SERVER_URL=http://docling-mcp-server.prod:5001
DOCLING_MCP_SERVER_TIMEOUT=600

# Neo4j MCP Server
NEO4J_MCP_SERVER_URL=http://neo4j-mcp-server.prod:3000
NEO4J_MCP_SERVER_TIMEOUT=600
NEO4J_URI=bolt://neo4j.prod:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-production-password

# Pinecone MCP Server
PINECONE_MCP_SERVER_URL=http://pinecone-mcp-server.prod:3000
PINECONE_MCP_SERVER_TIMEOUT=600
PINECONE_API_KEY=your-production-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=knowledgebot-prod-index
```

## Security Best Practices

1. **Use strong passwords** for all database connections
2. **Rotate API keys regularly** (especially AWS and Pinecone)
3. **Use different values for different environments** (staging vs production)
4. **Never commit secrets to code** - always use GitHub secrets
5. **Limit AWS IAM permissions** to only what's needed for deployment
6. **Use environment-specific prefixes** for resource names

## Verification

After setting up all secrets, you can verify they're working by:

1. **Triggering a deployment** via GitHub Actions
2. **Checking the deployment logs** for any missing environment variables
3. **Testing the MCP server connections** after deployment
4. **Monitoring the Lambda function logs** for connection errors

## Troubleshooting

### Common Issues

1. **"Secret not found" errors**: Make sure the secret name matches exactly (case-sensitive)
2. **Connection timeouts**: Check if the MCP server URLs are correct and accessible
3. **Authentication failures**: Verify that API keys and passwords are correct
4. **Permission errors**: Ensure AWS credentials have the necessary permissions

### Debug Steps

1. Check GitHub Actions logs for specific error messages
2. Verify all secrets are set in the repository settings
3. Test MCP server connectivity manually
4. Check AWS Lambda function environment variables
5. Review CloudWatch logs for detailed error information

## Support

If you encounter issues with the secret setup:

1. Check the GitHub Actions workflow logs
2. Verify all required secrets are present
3. Ensure secret values are correct and not expired
4. Contact the DevOps team for assistance

---

**Note**: This document should be kept secure and not committed to the repository if it contains sensitive information. Consider using a separate documentation repository or internal wiki for production secrets documentation.
