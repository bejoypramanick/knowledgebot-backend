# OpenAI AgentBuilder Configuration Guide

This guide provides step-by-step instructions for configuring the OpenAI AgentBuilder with the complete document ingestion and retrieval system.

## Prerequisites

1. OpenAI API key with access to GPT-4
2. Pinecone account and API key
3. Neo4j AuraDB account
4. AWS account with appropriate permissions
5. GitHub repository with Actions enabled

## Step 1: Set Up GitHub Actions Secrets

Navigate to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

### Required Secrets
```
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=pcsk_5bWrRg_EzH7xsyLtbCUHs5m2cmjitteDKvj6hzA3nytCPMvCshqqNHYPHvZMLxUAEvjzKo
PINECONE_ENVIRONMENT=gcp-starter
PINECONE_INDEX_NAME=chatbot-embeddings
NEO4J_URI=neo4j+s://APUPVZS7TOBGnEhwFhZcBBrPDlinyTH2ltHwesQhqTA.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=APUPVZS7TOBGnEhwFhZcBBrPDlinyTH2ltHwesQhqTA
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
```

## Step 2: Initialize External Services

Run the setup script to initialize all external services:

```bash
cd backend/agent-toolkit
./setup-external-services.sh
```

This script will:
- Set up Pinecone vector database
- Configure Neo4j knowledge graph
- Create DynamoDB tables
- Create S3 buckets

## Step 3: Deploy Lambda Functions

Deploy the agent-based Lambda functions:

```bash
./deploy.sh
```

This will:
- Build and push Docker images to ECR
- Create/update Lambda functions
- Set up S3 triggers
- Configure API Gateway

## Step 4: Configure OpenAI AgentBuilder

### 4.1 Access AgentBuilder

1. Go to [OpenAI AgentBuilder](https://platform.openai.com/agent-builder)
2. Sign in with your OpenAI account
3. Create a new agent or use the existing configuration

### 4.2 Document Ingestion Agent Configuration

#### Agent Details
- **Name**: Document Ingestion Agent
- **Description**: Handles document upload, processing, and storage in the knowledge base
- **Model**: GPT-4
- **Temperature**: 0.1
- **Max Tokens**: 2000

#### System Prompt
```
You are a Document Ingestion Agent responsible for processing uploaded documents and storing them in the knowledge base.

Your workflow:
1. Download document from S3 when triggered by S3 event
2. Process document using Docling to extract structured chunks
3. Store chunks in DynamoDB with metadata
4. Generate embeddings for all chunks using SentenceTransformers
5. Store embeddings in Pinecone vector database
6. Build knowledge graph in Neo4j with document and chunk relationships
7. Log processing status throughout the workflow

Important guidelines:
- Always handle errors gracefully and log status updates
- Process documents in the correct sequence
- Ensure all data is properly stored before marking as complete
- Use the document_id consistently across all storage systems
- Handle different document types (PDF, DOCX, TXT) appropriately

When you receive an S3 event, extract the bucket and key information and begin processing immediately.
```

#### Tools Configuration

Add the following tools to your agent:

1. **download_document_from_s3**
   - **Description**: Download a document from S3 bucket for processing
   - **Parameters**: s3_bucket (string), s3_key (string)

2. **process_document_with_docling**
   - **Description**: Process document using Docling to extract structured content and chunks
   - **Parameters**: document_data (object)

3. **store_chunks_in_dynamodb**
   - **Description**: Store processed document chunks in DynamoDB
   - **Parameters**: chunks (array), document_id (string)

4. **generate_embeddings_for_chunks**
   - **Description**: Generate embeddings for document chunks using SentenceTransformers
   - **Parameters**: chunks (array)

5. **store_embeddings_in_pinecone**
   - **Description**: Store generated embeddings in Pinecone vector database
   - **Parameters**: embeddings_data (array), document_id (string)

6. **build_knowledge_graph_in_neo4j**
   - **Description**: Build knowledge graph in Neo4j from document chunks
   - **Parameters**: chunks (array), document_id (string)

7. **log_processing_status**
   - **Description**: Log processing status and updates to DynamoDB
   - **Parameters**: document_id (string), status (string), message (string)

### 4.3 Retrieval Agent Configuration

#### Agent Details
- **Name**: Retrieval Agent
- **Description**: Handles query processing, context retrieval, and response generation
- **Model**: GPT-4
- **Temperature**: 0.2
- **Max Tokens**: 3000

#### System Prompt
```
You are a Retrieval Agent responsible for processing user queries and retrieving relevant context from the knowledge base.

Your workflow:
1. Receive user query from chat interface
2. Search Pinecone for semantically similar document chunks
3. Search Neo4j knowledge graph for related entities and relationships
4. Retrieve detailed chunk information from DynamoDB
5. Aggregate all retrieved context
6. Generate comprehensive response using the retrieved context

Important guidelines:
- Always search multiple sources to get comprehensive context
- Prioritize high-quality, relevant chunks for the response
- Handle cases where no relevant context is found
- Provide accurate citations and sources
- Ensure responses are helpful and contextually appropriate
- Use the aggregated context to generate informative responses

When you receive a query, immediately begin searching all available sources in parallel for maximum efficiency.
```

#### Tools Configuration

Add the following tools to your agent:

1. **search_pinecone_embeddings**
   - **Description**: Search for similar document chunks using Pinecone vector search
   - **Parameters**: query (string), limit (integer, default: 5)

2. **search_neo4j_knowledge_graph**
   - **Description**: Search knowledge graph in Neo4j for related entities and relationships
   - **Parameters**: query (string), limit (integer, default: 5)

3. **get_chunk_details_from_dynamodb**
   - **Description**: Get detailed chunk information from DynamoDB
   - **Parameters**: chunk_ids (array)

4. **aggregate_retrieval_context**
   - **Description**: Aggregate context from all retrieval sources (Pinecone, Neo4j, DynamoDB)
   - **Parameters**: pinecone_results (object), neo4j_results (object), dynamodb_chunks (object)

## Step 5: Configure Workflows

### 5.1 Document Ingestion Workflow

Create a new workflow with the following steps:

1. **Download Document** (download_document_from_s3)
   - Trigger: S3 Event
   - Required: Yes
   - Retry: 3 times
   - Timeout: 30 seconds

2. **Process with Docling** (process_document_with_docling)
   - Depends on: Download Document
   - Required: Yes
   - Retry: 2 times
   - Timeout: 60 seconds

3. **Store Chunks** (store_chunks_in_dynamodb)
   - Depends on: Process with Docling
   - Required: Yes
   - Retry: 3 times
   - Timeout: 30 seconds

4. **Generate Embeddings** (generate_embeddings_for_chunks)
   - Depends on: Store Chunks
   - Required: Yes
   - Retry: 2 times
   - Timeout: 45 seconds

5. **Store in Pinecone** (store_embeddings_in_pinecone)
   - Depends on: Generate Embeddings
   - Required: Yes
   - Retry: 3 times
   - Timeout: 30 seconds

6. **Build Knowledge Graph** (build_knowledge_graph_in_neo4j)
   - Depends on: Store Chunks
   - Required: Yes
   - Retry: 2 times
   - Timeout: 45 seconds

7. **Log Completion** (log_processing_status)
   - Depends on: Store in Pinecone, Build Knowledge Graph
   - Required: Yes
   - Retry: 1 time
   - Timeout: 10 seconds

### 5.2 Retrieval Workflow

Create a new workflow with the following steps:

1. **Search Pinecone** (search_pinecone_embeddings)
   - Parallel: Yes
   - Required: Yes
   - Retry: 2 times
   - Timeout: 15 seconds

2. **Search Neo4j** (search_neo4j_knowledge_graph)
   - Parallel: Yes
   - Required: Yes
   - Retry: 2 times
   - Timeout: 15 seconds

3. **Get Chunk Details** (get_chunk_details_from_dynamodb)
   - Depends on: Search Pinecone, Search Neo4j
   - Required: Yes
   - Retry: 2 times
   - Timeout: 10 seconds

4. **Aggregate Context** (aggregate_retrieval_context)
   - Depends on: Get Chunk Details
   - Required: Yes
   - Retry: 1 time
   - Timeout: 10 seconds

## Step 6: Test the System

### 6.1 Test Document Upload

1. Use the presigned URL endpoint to get an upload URL:
   ```bash
   curl -X POST "https://your-api-gateway-url/retrieve" \
     -H "Content-Type: application/json" \
     -d '{"action": "get-upload-url", "filename": "test.pdf", "content_type": "application/pdf"}'
   ```

2. Upload a PDF document to the returned presigned URL

3. Check the Lambda logs to see the processing workflow

### 6.2 Test Document Retrieval

1. Query the retrieval endpoint:
   ```bash
   curl -X POST "https://your-api-gateway-url/retrieve" \
     -H "Content-Type: application/json" \
     -d '{"query": "your search query", "limit": 5}'
   ```

2. Verify that relevant chunks are returned with proper metadata

## Step 7: Monitor and Maintain

### 7.1 Monitoring

- Check CloudWatch logs for Lambda functions
- Monitor Pinecone index usage and performance
- Track Neo4j database performance
- Monitor DynamoDB read/write capacity

### 7.2 Maintenance

- Regularly update dependencies
- Monitor storage usage in S3
- Clean up old embeddings if needed
- Optimize Neo4j queries for better performance

## Troubleshooting

### Common Issues

1. **Pinecone Connection Failed**
   - Verify API key and environment
   - Check index name and dimension

2. **Neo4j Connection Failed**
   - Verify URI, username, and password
   - Check network connectivity

3. **DynamoDB Access Denied**
   - Verify IAM permissions
   - Check table names and region

4. **S3 Upload Failed**
   - Verify bucket permissions
   - Check presigned URL expiration

### Debug Steps

1. Check Lambda function logs in CloudWatch
2. Verify environment variables are set correctly
3. Test individual functions in isolation
4. Check external service connectivity

## Support

For additional support:
- Check the GitHub repository issues
- Review AWS CloudWatch logs
- Consult OpenAI documentation
- Check Pinecone and Neo4j documentation
