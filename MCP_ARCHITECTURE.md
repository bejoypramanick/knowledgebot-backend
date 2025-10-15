# KnowledgeBot MCP Architecture

## Overview

This project implements a clean Microservice Context Protocol (MCP) architecture where an LLM agent intelligently routes queries to appropriate MCP servers for different data operations.

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   LLM Agent         │───▶│  Universal MCP Client│───▶│ Official MCP Servers│
│   (OpenAI API)      │    │   (JSON-RPC Router)  │    │                     │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                                                        │
                                                                        ▼
                                                              ┌─────────────────────┐
                                                              │  Data Sources       │
                                                              │  ├── Pinecone DB    │
                                                              │  ├── DynamoDB       │
                                                              │  ├── Docling        │
                                                              │  ├── Neo4j Cypher   │
                                                              │  └── Neo4j Modeling │
                                                              └─────────────────────┘
```

## MCP Servers

### 1. Docling MCP Server
- **Purpose**: Document processing and parsing
- **Dockerfile**: `Dockerfile.docling-library`
- **Lambda Function**: `docling-mcp-server`
- **Capabilities**: Text extraction, chunking, document analysis

### 2. Pinecone MCP Server
- **Purpose**: Vector search and similarity search
- **Dockerfile**: `Dockerfile.pinecone-mcp`
- **Lambda Function**: `pinecone-mcp-server`
- **Capabilities**: Semantic search, document indexing, vector operations
- **Based on**: Official `@pinecone-database/mcp` NPM package

### 3. DynamoDB MCP Server
- **Purpose**: Database table operations
- **Dockerfile**: `Dockerfile.dynamodb-mcp`
- **Lambda Function**: `dynamodb-mcp-server`
- **Capabilities**: CRUD operations, table management, data storage
- **Based on**: Official `awslabs/dynamodb-mcp-server` Docker image

### 4. Neo4j Cypher MCP Server
- **Purpose**: Graph database query operations
- **Dockerfile**: `Dockerfile.neo4j-cypher-mcp`
- **Lambda Function**: `neo4j-cypher-mcp-server`
- **Capabilities**: Cypher query execution, graph data retrieval
- **Based on**: Official `mcp-neo4j-cypher@0.4.1` package

### 5. Neo4j Data Modeling MCP Server
- **Purpose**: Graph schema design and validation
- **Dockerfile**: `Dockerfile.neo4j-data-modeling-mcp`
- **Lambda Function**: `neo4j-modeling-mcp-server`
- **Capabilities**: Node/relationship creation, schema validation
- **Based on**: Official `mcp/neo4j-data-modeling` Docker image

## Key Components

### Universal MCP Client
- **File**: `microservices/mcp-client.py`
- **Purpose**: Communicates with all MCP servers via JSON-RPC
- **Features**: Async context manager, error handling, health checks

### LLM Agent Example
- **File**: `examples/llm-agent-example.py`
- **Purpose**: Shows how to use OpenAI API with MCP servers
- **Features**: Intelligent query routing, natural language processing

## Query Routing

The LLM agent intelligently determines which MCP server to use based on query content:

| Query Type | MCP Server | Example |
|------------|------------|---------|
| Document processing | Docling MCP | "Process this PDF document" |
| Vector search | Pinecone MCP | "Find similar documents" |
| Database operations | DynamoDB MCP | "List all tables" |
| Graph queries | Neo4j Cypher MCP | "Find users connected to John" |
| Graph modeling | Neo4j Modeling MCP | "Create a new Person node" |

## Deployment

### GitHub Actions Workflow
- **File**: `.github/workflows/deploy.yml`
- **Features**: 
  - Parallel Docker builds for all MCP servers
  - ECR repository creation and lifecycle policies
  - Lambda function deployment with Function URLs
  - Automatic cleanup of redundant resources

### AWS Resources

#### Lambda Functions
- `docling-mcp-server`
- `pinecone-mcp-server`
- `dynamodb-mcp-server`
- `neo4j-cypher-mcp-server`
- `neo4j-modeling-mcp-server`

#### ECR Repositories
- `knowledgebot-docling-mcp`
- `knowledgebot-pinecone-mcp`
- `knowledgebot-dynamodb-mcp`
- `knowledgebot-neo4j-cypher-mcp`
- `knowledgebot-neo4j-modeling-mcp`

#### IAM Role
- `mcp-lambda-execution-role` (with basic execution permissions)

## Environment Variables

### Required Secrets
- `PINECONE_API_KEY`
- `PINECONE_ENVIRONMENT`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`

## Cleanup

### Automated Cleanup
The GitHub Actions workflow automatically removes redundant resources:
- Old Lambda functions
- Unused DynamoDB tables
- Redundant S3 buckets
- Old IAM roles

### Manual Cleanup
Use the cleanup script to manually remove redundant resources:
```bash
./scripts/cleanup-aws-resources.sh
```

## Benefits

✅ **Clean Architecture**: Only essential MCP servers, no redundant components
✅ **Official Tools**: Uses official MCP servers where available
✅ **Intelligent Routing**: LLM agent determines appropriate MCP server
✅ **Cost Effective**: Removes unused AWS resources
✅ **Scalable**: Easy to add new MCP servers
✅ **Production Ready**: Based on official tools and best practices

## Usage

### Example: Using the LLM Agent
```python
from examples.llm_agent_example import IntelligentLLMAgent

agent = IntelligentLLMAgent(openai_api_key="your-key")

# The agent will intelligently route this query
result = await agent.process_query("Find documents about machine learning")
```

### Example: Direct MCP Client Usage
```python
from microservices.mcp_client import UniversalMCPClient

async with UniversalMCPClient() as client:
    # Search Pinecone
    results = await client.pinecone_search("machine learning", "my-index")
    
    # Query Neo4j
    nodes = await client.neo4j_execute_query("MATCH (n:Person) RETURN n LIMIT 10")
    
    # List DynamoDB tables
    tables = await client.dynamodb_list_tables()
```

This architecture provides a clean, efficient, and scalable foundation for AI-powered data operations using the MCP protocol.
