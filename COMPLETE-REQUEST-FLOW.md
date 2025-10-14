# 🚀 Complete KnowledgeBot Request Flow

## 📋 System Overview

This document provides a comprehensive view of all request flows in the KnowledgeBot system, showing how different components interact to process documents and answer queries.

---

## 🏗️ Architecture Components

### **ZIP Lambdas (Business Logic)**
- `chat-orchestrator-business-logic.py` - Chat query processing
- `document-processor-business-logic.py` - Document processing pipeline
- `dynamodb-crud-handler.py` - DynamoDB operations
- `s3-unified-handler.py` - S3 operations

### **Docker Lambdas (Library Functions)**
- `docling-library-handler.py` - Document processing library
- `sentence-transformer-library-handler.py` - Text embeddings
- `pinecone-library-handler.py` - Vector database operations
- `neo4j-library-handler.py` - Knowledge graph operations
- `openai-library-handler.py` - AI response generation

### **AWS Services**
- **API Gateway** - Request routing and CORS
- **S3** - File storage
- **DynamoDB** - Document metadata and chunks
- **Pinecone** - Vector similarity search
- **Neo4j** - Knowledge graph database
- **OpenAI API** - AI response generation

---

## 🔄 Complete Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT APPLICATION                                    │
│  • Web Application                                                              │
│  • Mobile App                                                                   │
│  • API Client                                                                   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │ HTTP/HTTPS Requests
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                        │
│  • Request Routing                                                              │
│  • CORS Handling                                                                │
│  • Rate Limiting                                                                │
│  • Authentication                                                               │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │ Routes based on endpoint
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        REQUEST ROUTING                                          │
│                                                                                 │
│  📄 Document Upload    💬 Chat Query      🗄️ CRUD Operations                   │
│  /upload/*            /chat/*            /crud/*                               │
│       │                    │                    │                               │
│       ▼                    ▼                    ▼                               │
└───────┼────────────────────┼────────────────────┼─────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
```

---

## 📄 DOCUMENT UPLOAD FLOW

### **Step 1: Presigned URL Generation**
```
Client Request: POST /upload/presigned-url
└── API Gateway
    └── s3-unified-handler.py (ZIP LAMBDA)
        ├── Validates request
        ├── Generates presigned URL
        └── Returns upload URL to client
```

### **Step 2: Direct S3 Upload**
```
Client Upload: PUT to S3 presigned URL
└── S3 Bucket
    ├── Stores file directly
    └── Triggers S3 event notification
```

### **Step 3: Document Processing Pipeline**
```
S3 Event Trigger
└── document-processor-business-logic.py (ZIP LAMBDA)
    ├── Downloads document from S3
    ├── Orchestrates processing pipeline
    └── Calls multiple Docker Lambdas:
        │
        ├── docling-library-handler.py (DOCKER LAMBDA)
        │   ├── Processes document (PDF, DOCX, etc.)
        │   ├── Extracts text and structure
        │   └── Returns processed content
        │
        ├── sentence-transformer-library-handler.py (DOCKER LAMBDA)
        │   ├── Generates embeddings for document chunks
        │   ├── Uses pre-trained models
        │   └── Returns vector embeddings
        │
        ├── pinecone-library-handler.py (DOCKER LAMBDA)
        │   ├── Stores embeddings in Pinecone
        │   ├── Creates vector index entries
        │   └── Returns storage confirmation
        │
        └── neo4j-library-handler.py (DOCKER LAMBDA)
            ├── Creates knowledge graph relationships
            ├── Stores document metadata and connections
            └── Returns graph update confirmation
```

### **Step 4: Direct Storage Operations**
```
document-processor-business-logic.py (ZIP LAMBDA)
├── Stores document metadata in DynamoDB
├── Saves processed markdown to S3
└── Updates processing status
```

---

## 💬 CHAT QUERY FLOW

### **Step 1: Query Processing**
```
Client Request: POST /chat/query
└── API Gateway
    └── chat-orchestrator-business-logic.py (ZIP LAMBDA)
        ├── Receives user query
        ├── Orchestrates query processing pipeline
        └── Calls multiple Docker Lambdas:
```

### **Step 2: Library Lambda Invocations**
```
chat-orchestrator-business-logic.py (ZIP LAMBDA)
├── sentence-transformer-library-handler.py (DOCKER LAMBDA)
│   ├── Generates query embeddings
│   ├── Converts user question to vector
│   └── Returns query embedding
│
├── pinecone-library-handler.py (DOCKER LAMBDA)
│   ├── Searches similar document chunks
│   ├── Performs vector similarity search
│   └── Returns relevant document chunks
│
├── neo4j-library-handler.py (DOCKER LAMBDA)
│   ├── Queries knowledge graph for context
│   ├── Finds related entities and relationships
│   └── Returns graph-based context
│
└── openai-library-handler.py (DOCKER LAMBDA)
    ├── Generates AI response using GPT
    ├── Combines context + query for final answer
    └── Returns generated response
```

### **Step 3: Direct Operations**
```
chat-orchestrator-business-logic.py (ZIP LAMBDA)
├── Queries DynamoDB for chat history
├── Stores conversation context
└── Updates user interaction logs
```

### **Step 4: Response Generation**
```
chat-orchestrator-business-logic.py (ZIP LAMBDA)
├── Formats final response
├── Includes sources and citations
└── Returns to client via API Gateway
```

---

## 🗄️ CRUD OPERATIONS FLOW

### **DynamoDB Operations**
```
Client Request: GET/POST/PUT/DELETE /crud/documents/*
└── API Gateway
    └── dynamodb-crud-handler.py (ZIP LAMBDA)
        ├── Receives CRUD request
        ├── Performs direct DynamoDB operations
        └── Returns operation results
```

### **S3 Operations**
```
Client Request: GET/POST/PUT/DELETE /crud/files/*
└── API Gateway
    └── s3-unified-handler.py (ZIP LAMBDA)
        ├── Receives S3 request
        ├── Performs direct S3 operations
        └── Returns operation results
```

---

## 🔗 INTER-SERVICE COMMUNICATION PATTERNS

### **Lambda-to-Lambda Invocation**
```
ZIP LAMBDA → lambda_client.invoke() → DOCKER LAMBDA

Example:
response = lambda_client.invoke(
    FunctionName='sentence-transformer-library-handler',
    InvocationType='RequestResponse',
    Payload=json.dumps({'texts': [user_query]})
)
```

### **Direct AWS Service Access**
```
ZIP LAMBDA → boto3 client → AWS Service

Examples:
- dynamodb = boto3.resource('dynamodb')
- s3_client = boto3.client('s3')
```

### **Event-Driven Triggers**
```
S3 Event → Lambda Function

Example:
S3 upload → document-processor-business-logic.py
```

---

## 📊 API ENDPOINTS SUMMARY

### **Document Upload Endpoints**
| Method | Endpoint | Lambda Function | Purpose |
|--------|----------|-----------------|---------|
| `POST` | `/upload/presigned-url` | `s3-unified-handler` | Generate S3 presigned URL |
| `POST` | `/upload/complete` | `document-processor-business-logic` | Process uploaded document |

### **Chat Query Endpoints**
| Method | Endpoint | Lambda Function | Purpose |
|--------|----------|-----------------|---------|
| `POST` | `/chat/query` | `chat-orchestrator-business-logic` | Process chat queries |
| `POST` | `/chat/history` | `chat-orchestrator-business-logic` | Get chat history |

### **CRUD Operations Endpoints**
| Method | Endpoint | Lambda Function | Purpose |
|--------|----------|-----------------|---------|
| `GET` | `/crud/documents` | `dynamodb-crud-handler` | List documents |
| `GET` | `/crud/documents/{id}` | `dynamodb-crud-handler` | Get document details |
| `PUT` | `/crud/documents/{id}` | `dynamodb-crud-handler` | Update document |
| `DELETE` | `/crud/documents/{id}` | `dynamodb-crud-handler` | Delete document |
| `GET` | `/crud/files` | `s3-unified-handler` | List S3 files |
| `GET` | `/crud/files/{key}` | `s3-unified-handler` | Download file |

---

## 🔄 DATA FLOW SUMMARY

### **Document Processing Data Flow**
```
Document Upload → S3 → Document Processor → Library Lambdas → Storage
                                                              ├── DynamoDB (metadata)
                                                              ├── S3 (markdown)
                                                              ├── Pinecone (vectors)
                                                              └── Neo4j (graph)
```

### **Chat Query Data Flow**
```
User Query → Chat Orchestrator → Library Lambdas → AI Response
                              ├── Sentence Transformer (embeddings)
                              ├── Pinecone (vector search)
                              ├── Neo4j (graph context)
                              ├── DynamoDB (additional context)
                              └── OpenAI (response generation)
```

---

## 🎯 KEY ARCHITECTURAL BENEFITS

### **ZIP Lambdas (Business Logic)**
- ✅ **Viewable Code**: All business logic visible in AWS Lambda console
- ✅ **Fast Cold Starts**: Lightweight, quick initialization
- ✅ **Direct AWS Access**: Can access DynamoDB and S3 directly
- ✅ **Comprehensive Logging**: Detailed execution tracking
- ✅ **Easy Debugging**: Source code available for troubleshooting

### **Docker Lambdas (Library Functions)**
- ✅ **Heavy Library Management**: Complex ML/AI libraries isolated
- ✅ **Optimized Performance**: Pre-installed dependencies
- ✅ **Reusable Components**: Shared across multiple business flows
- ✅ **Version Control**: Library versions managed in Docker images
- ✅ **Scalable**: Independent scaling based on usage

### **Inter-Service Communication**
- ✅ **Synchronous Calls**: RequestResponse pattern for immediate results
- ✅ **Error Handling**: Comprehensive error propagation and logging
- ✅ **JSON Communication**: Standardized payload format
- ✅ **Retry Mechanisms**: Built-in Lambda retry for transient failures

---

## 🚀 DEPLOYMENT FLOW

### **GitHub Actions Workflows**
1. **Docker Lambdas Deployment**
   - Triggers on library handler changes
   - Builds Docker images
   - Pushes to ECR
   - Deploys Lambda functions

2. **Zip Lambdas Deployment**
   - Triggers on business logic changes
   - Creates zip packages
   - Deploys Lambda functions
   - Sets environment variables

3. **All Lambdas Deployment**
   - Orchestrates both deployments
   - Provides deployment summary

---

## 🔧 ENVIRONMENT VARIABLES

### **Library Function Names**
```bash
DOCLING_LIBRARY_FUNCTION=docling-library-handler
PINECONE_LIBRARY_FUNCTION=pinecone-library-handler
NEO4J_LIBRARY_FUNCTION=neo4j-library-handler
OPENAI_LIBRARY_FUNCTION=openai-library-handler
SENTENCE_TRANSFORMER_LIBRARY_FUNCTION=sentence-transformer-library-handler
```

### **Database Configuration**
```bash
CHUNKS_TABLE=document-chunks
PROCESSED_DOCUMENTS_BUCKET=processed-documents
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

---

## 📈 MONITORING AND LOGGING

### **CloudWatch Logs**
- Each Lambda function logs its operations
- Structured logging with context
- Performance metrics tracking
- Error tracking and debugging

### **Logging Format**
```python
logger.info(f"🚀 Starting document processing pipeline for: {filename}")
logger.info(f"🔧 Calling Docling library for document: {filename}")
logger.info(f"✅ Docling library processed successfully: {chunks} chunks")
logger.error(f"❌ Error calling Docling library: {e}")
```

---

This complete request flow provides a comprehensive understanding of how the KnowledgeBot system processes requests, from initial client interaction through all the various Lambda functions and AWS services to the final response delivery.
