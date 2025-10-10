# GitHub Actions Deployment Setup Guide

## Required GitHub Repository Secrets

To enable complete end-to-end deployment via GitHub Actions, you need to configure the following secrets in your GitHub repository:

### 1. AWS Configuration Secrets
- `AWS_ACCOUNT_ID`: `090163643302` (Your AWS Account ID)
- `AWS_ACCESS_KEY_ID`: Your AWS Access Key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Access Key

### 2. Service-Specific Secrets (Optional - only if using those services)

#### Pinecone Configuration
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_INDEX_NAME`: Your Pinecone index name
- `PINECONE_HOST`: Your Pinecone host URL
- `PINECONE_DIMENSIONS`: Vector dimensions (e.g., "1536")
- `PINECONE_ENVIRONMENT`: Your Pinecone environment
- `PINECONE_METRIC`: Distance metric (e.g., "cosine")

#### Neo4j Configuration
- `NEO4J_URI`: Your Neo4j database URI
- `NEO4J_USER`: Your Neo4j username
- `NEO4J_PASSWORD`: Your Neo4j password

#### OpenAI Configuration
- `OPENAI_API_KEY`: Your OpenAI API key

## How to Set GitHub Secrets

1. Go to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click on **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add each secret with the exact name and value listed above

## IAM Role Requirements

The GitHub Actions workflow uses the IAM role `lambda-execution-role` which has been created with the following permissions:
- `AWSLambdaBasicExecutionRole` - For basic Lambda execution
- `AmazonS3FullAccess` - For S3 operations (presigned URLs)

## Fixed Issues

✅ **IAM Role ARN**: Fixed to use correct format `arn:aws:iam::090163643302:role/lambda-execution-role`
✅ **Environment Variables**: Removed `AWS_REGION` (reserved variable) from Lambda environment
✅ **Empty Environment Variables**: Added proper handling for services without environment variables

## Deployment Process

Once all secrets are configured:

1. **Push to main/develop branch** - Triggers automatic deployment
2. **Manual trigger** - Use "Actions" tab → "Build and Deploy All Micro-Services" → "Run workflow"

The workflow will:
1. Build all Docker images in parallel
2. Push images to ECR
3. Create/update Lambda functions with correct IAM role ARN
4. Set appropriate environment variables per service

## Services Deployed

The workflow deploys the following microservices:
- `knowledgebot-presigned-url`
- `knowledgebot-pinecone-search`
- `knowledgebot-pinecone-upsert`
- `knowledgebot-neo4j-search`
- `knowledgebot-neo4j-write`
- `knowledgebot-dynamodb-crud`
- `knowledgebot-text-chunker`
- `knowledgebot-embedding-generator`
- `knowledgebot-rag-search`
- `knowledgebot-chat-generator`
- `knowledgebot-s3-reader`
- `knowledgebot-pdf-processor`
- `knowledgebot-easyocr`
- `knowledgebot-table-detector`
- `knowledgebot-docling-core`
- `knowledgebot-docling-full`

## Troubleshooting

If deployment fails:
1. Check that `AWS_ACCOUNT_ID` secret is set to `090163643302`
2. Verify AWS credentials have sufficient permissions
3. Ensure IAM role `lambda-execution-role` exists in your AWS account
4. Check GitHub Actions logs for specific error messages
