# 🧠 KnowledgeBot Backend

A serverless chatbot backend system using OpenAI AgentToolkit with CRUD tools and AI intelligence.

## 🏗️ Architecture

The system uses a **perfect separation of concerns**:
- **CRUD Tools**: Pure data operations only
- **AI Model**: All business logic and intelligence
- **2 Lambda Functions**: Chat and document processing

### Chat Flow
```
User Query → chatbot-chat-agent → AI Agent → CRUD Tools → Response
```

### Document Processing Flow
```
S3 Upload → chatbot-document-agent → AI Agent → CRUD Tools → Knowledge Base
```

## 📁 Repository Structure

```
knowledgebot-backend/
├── backend/
│   ├── agent-toolkit/           # Main agent implementation
│   │   ├── unified_ai_agent.py  # Unified AI agent with CRUD tools
│   │   ├── lambda_handlers.py   # Lambda function handlers
│   │   ├── crud_operations.py   # Pure CRUD operations
│   │   ├── deploy_agents.sh     # Deployment script
│   │   ├── requirements.txt     # Python dependencies
│   │   ├── Dockerfile           # Container configuration
│   │   └── *.md                 # Documentation
│   ├── lambda/
│   │   └── shared/              # Shared utilities
│   │       └── error_handler.py
│   └── [other backend files]
├── build_base_images.sh         # Base image build script
├── build_state.json            # Build state tracking
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **OpenAI API Key** with GPT-4 access
3. **Pinecone Account** (optional - for vector search)
4. **Neo4j AuraDB Account** (optional - for knowledge graph)
5. **DynamoDB Tables** (for data storage)

### Step 1: Set Environment Variables

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export PINECONE_API_KEY="your_pinecone_api_key"  # Optional
export PINECONE_ENVIRONMENT="gcp-starter"        # Optional
export PINECONE_INDEX_NAME="chatbot-embeddings"  # Optional
export NEO4J_URI="your_neo4j_uri"               # Optional
export NEO4J_USER="neo4j"                       # Optional
export NEO4J_PASSWORD="your_neo4j_password"     # Optional
export AWS_REGION="ap-south-1"
export DOCUMENTS_BUCKET="your-documents-bucket"
export KNOWLEDGE_BASE_TABLE="your-knowledge-table"
```

### Step 2: Deploy the Agents

```bash
cd backend/agent-toolkit
./deploy_agents.sh
```

This will:
- ✅ Create/update 2 Lambda functions
- ✅ Set up environment variables
- ✅ Deploy the unified agent system

### Step 3: Test the System

```bash
# Test chat endpoint
curl -X POST 'https://your-api-gateway-url/chat' \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hello, how can you help me?"}'

# Test document processing
aws s3 cp test-document.pdf s3://your-documents-bucket/documents/
```

## 🔧 CRUD Operations Available

### S3 Operations:
- `read_s3_data_tool(bucket, key)` - Read raw S3 data

### Pinecone Operations:
- `search_pinecone_tool(query_vector, limit)` - Search vectors
- `upsert_pinecone_tool(vectors, namespace)` - Store vectors
- `delete_pinecone_tool(ids, namespace)` - Delete vectors

### Neo4j Operations:
- `search_neo4j_tool(cypher_query, parameters)` - Execute Cypher
- `execute_neo4j_write_tool(cypher_query, parameters)` - Write to graph

### DynamoDB Operations:
- `read_dynamodb_tool(table_name, key)` - Read single item
- `batch_read_dynamodb_tool(table_name, keys)` - Batch read
- `write_dynamodb_tool(table_name, item)` - Write item
- `update_dynamodb_tool(table_name, key, update_expression, values)` - Update
- `delete_dynamodb_tool(table_name, key)` - Delete item

### Embedding Operations:
- `generate_embedding_tool(text)` - Generate vector

## 🧠 AI Agent Capabilities

The unified AI agent handles:
- ✅ **Business logic** and decision making
- ✅ **Query understanding** and intent analysis
- ✅ **Data processing** and synthesis
- ✅ **Response generation** and formatting
- ✅ **Error handling** and user guidance
- ✅ **Multi-question processing**
- ✅ **Context awareness** and conversation flow

## 🚀 Lambda Functions

### 1. `chatbot-chat-agent`
- **Purpose**: Handles all chat interactions
- **Handler**: `lambda_handlers.lambda_handler_knowledge_chat`
- **Capabilities**: 
  - Natural language understanding
  - Knowledge retrieval and synthesis
  - Multi-question processing
  - Contextual responses

### 2. `chatbot-document-agent`
- **Purpose**: Handles document processing and ingestion
- **Handler**: `lambda_handlers.lambda_handler_knowledge_document_ingestion`
- **Capabilities**:
  - Document parsing and processing
  - Embedding generation and storage
  - Knowledge graph construction
  - Metadata management

## 📦 Dependencies

See `backend/agent-toolkit/requirements.txt` for complete Python dependencies.

Key dependencies:
- `openai>=1.0.0` - OpenAI AgentToolkit
- `boto3>=1.26.0` - AWS SDK
- `pinecone-client>=2.2.0` - Vector database
- `neo4j>=5.0.0` - Graph database
- `sentence-transformers>=2.2.0` - Embeddings

## 🔧 Configuration

### Environment Variables
All configuration is handled through environment variables:

```bash
# OpenAI
OPENAI_API_KEY

# Pinecone (Optional)
PINECONE_API_KEY
PINECONE_ENVIRONMENT
PINECONE_INDEX_NAME

# Neo4j (Optional)
NEO4J_URI
NEO4J_USER
NEO4J_PASSWORD

# AWS
AWS_REGION
DOCUMENTS_BUCKET
EMBEDDINGS_BUCKET
KNOWLEDGE_BASE_TABLE
METADATA_TABLE
```

### Lambda Configuration
- **Memory**: 3008 MB (for document processing)
- **Timeout**: 900 seconds (15 minutes)
- **Runtime**: Python 3.9 (Docker container)

## 📊 Monitoring

### CloudWatch Logs
- Lambda function execution logs
- Error tracking and debugging
- Performance metrics

### Service Monitoring
- Pinecone index usage and performance
- Neo4j database query performance
- DynamoDB read/write capacity
- S3 storage usage

## 🔒 Security

### IAM Permissions
- Least privilege access for Lambda functions
- Separate policies for different operations
- Regular permission audits

### Data Encryption
- S3 server-side encryption
- DynamoDB encryption at rest
- Secure transmission for all API calls

## 🚨 Troubleshooting

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

## 📈 Performance Optimization

### Lambda Optimization
- Use provisioned concurrency for consistent performance
- Optimize memory allocation based on usage
- Implement connection pooling for external services

### Database Optimization
- Use DynamoDB on-demand billing for variable workloads
- Implement caching for frequently accessed data
- Optimize Neo4j queries with proper indexing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the KnowledgeBot system. Please refer to the main project license.

## 🆘 Support

For support and questions:
- Check the GitHub repository issues
- Review CloudWatch logs
- Consult the troubleshooting guide
- Contact the development team

---

**Built with ❤️ using OpenAI AgentToolkit, AWS Lambda, and modern AI technologies.**
