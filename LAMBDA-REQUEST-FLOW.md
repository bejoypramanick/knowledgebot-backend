# Lambda Request Flow & Inter-Service Communication

## 🚀 Complete Request Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT APPLICATION                                    │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │ HTTP Requests
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                        │
│  • Routes requests to appropriate Lambda functions                              │
│  • Handles CORS and authentication                                             │
│  • Manages rate limiting and throttling                                        │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │ Routes based on endpoint
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        REQUEST ROUTING                                          │
│                                                                                 │
│  📄 Document Upload    💬 Chat Query      🗄️ CRUD Operations                   │
│  /upload              /chat              /crud                                 │
│       │                    │                    │                               │
│       ▼                    ▼                    ▼                               │
└───────┼────────────────────┼────────────────────┼─────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
```

## 📄 DOCUMENT UPLOAD FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DOCUMENT UPLOAD PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

1. 📋 S3 UNIFIED HANDLER (ZIP LAMBDA)
   ├── Generates presigned URL for client upload
   ├── Returns upload URL to client
   └── Client uploads file directly to S3

2. ☁️ S3 EVENT TRIGGER
   ├── S3 triggers document-processor-business-logic
   └── Passes file metadata (bucket, key, etc.)

3. 📄 DOCUMENT PROCESSOR BUSINESS LOGIC (ZIP LAMBDA)
   ├── Downloads file from S3
   ├── Orchestrates processing pipeline
   └── Calls multiple Docker Lambdas:

   ┌─────────────────────────────────────────────────────────────────────────────┐
   │                    LIBRARY LAMBDA INVOCATIONS                               │
   └─────────────────────────────────────────────────────────────────────────────┘

   🔧 DOCLING LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Processes document (PDF, DOCX, etc.)
   ├── Extracts text and structure
   └── Returns processed content

   🧠 SENTENCE TRANSFORMER LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Generates embeddings for document chunks
   ├── Uses pre-trained models
   └── Returns vector embeddings

   🔍 PINECONE LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Stores embeddings in Pinecone vector database
   ├── Creates vector index entries
   └── Returns storage confirmation

   🕸️ NEO4J LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Creates knowledge graph relationships
   ├── Stores document metadata and connections
   └── Returns graph update confirmation

4. 💾 DIRECT OPERATIONS (ZIP LAMBDA)
   ├── Stores document metadata in DynamoDB
   ├── Saves processed markdown to S3
   └── Updates processing status

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INVOCATION PATTERN                                   │
│                                                                                 │
│  ZIP LAMBDA → lambda_client.invoke() → DOCKER LAMBDA                          │
│                                                                                 │
│  Example:                                                                       │
│  response = lambda_client.invoke(                                              │
│      FunctionName='docling-library-handler',                                   │
│      InvocationType='RequestResponse',                                          │
│      Payload=json.dumps({'document': document_data})                           │
│  )                                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 💬 CHAT QUERY FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CHAT QUERY PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

1. 💬 CHAT ORCHESTRATOR BUSINESS LOGIC (ZIP LAMBDA)
   ├── Receives user query from API Gateway
   ├── Orchestrates query processing pipeline
   └── Calls multiple Docker Lambdas:

   ┌─────────────────────────────────────────────────────────────────────────────┐
   │                    LIBRARY LAMBDA INVOCATIONS                               │
   └─────────────────────────────────────────────────────────────────────────────┘

   🧠 SENTENCE TRANSFORMER LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Generates query embeddings
   ├── Converts user question to vector
   └── Returns query embedding

   🔍 PINECONE LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Searches similar document chunks
   ├── Performs vector similarity search
   └── Returns relevant document chunks

   🕸️ NEO4J LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Queries knowledge graph for context
   ├── Finds related entities and relationships
   └── Returns graph-based context

   🤖 OPENAI LIBRARY HANDLER (DOCKER LAMBDA)
   ├── Generates AI response using GPT
   ├── Combines context + query for final answer
   └── Returns generated response

2. 💾 DIRECT OPERATIONS (ZIP LAMBDA)
   ├── Queries DynamoDB for chat history
   ├── Stores conversation context
   └── Updates user interaction logs

3. 📤 RESPONSE GENERATION
   ├── Formats final response
   ├── Includes sources and citations
   └── Returns to client via API Gateway

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INVOCATION PATTERN                                   │
│                                                                                 │
│  ZIP LAMBDA → lambda_client.invoke() → DOCKER LAMBDA                          │
│                                                                                 │
│  Example:                                                                       │
│  response = lambda_client.invoke(                                              │
│      FunctionName='sentence-transformer-library-handler',                      │
│      InvocationType='RequestResponse',                                          │
│      Payload=json.dumps({'texts': [user_query]})                              │
│  )                                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🗄️ CRUD OPERATIONS FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CRUD OPERATIONS PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

1. 🗄️ DYNAMODB CRUD HANDLER (ZIP LAMBDA)
   ├── Receives CRUD request from API Gateway
   ├── Performs direct DynamoDB operations
   └── No library Lambda calls needed

   Operations:
   ├── CREATE: Insert new document metadata
   ├── READ: Query document information
   ├── UPDATE: Modify document properties
   └── DELETE: Remove document records

2. 💾 DIRECT DYNAMODB OPERATIONS
   ├── Uses boto3 DynamoDB resource
   ├── Handles table operations directly
   └── Returns operation results

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INVOCATION PATTERN                                   │
│                                                                                 │
│  API GATEWAY → DYNAMODB CRUD HANDLER (ZIP LAMBDA) → DYNAMODB                   │
│                                                                                 │
│  No inter-Lambda communication needed for CRUD operations                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 INTER-SERVICE COMMUNICATION PATTERNS

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMMUNICATION ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ZIP LAMBDAS   │    │  DOCKER LAMBDAS │    │   AWS SERVICES  │
│  (Business      │    │  (Library       │    │   (Storage &    │
│   Logic)        │    │   Functions)    │    │    Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • chat-orchestrator│    │ • docling-library│    │ • DynamoDB      │
│ • document-processor│    │ • sentence-transformer│ │ • S3           │
│ • dynamodb-crud   │    │ • pinecone-library│    │ • Pinecone      │
│ • s3-unified      │    │ • neo4j-library │    │ • Neo4j         │
│                   │    │ • openai-library│    │ • OpenAI API    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INVOCATION METHODS                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

1. 🔗 LAMBDA-TO-LAMBDA INVOCATION
   ├── Uses boto3 lambda_client.invoke()
   ├── Synchronous RequestResponse calls
   ├── Payload passed as JSON
   └── Response returned as JSON

2. 📡 API GATEWAY INTEGRATION
   ├── HTTP requests routed to Lambda functions
   ├── CORS headers handled automatically
   ├── Request/response transformation
   └── Error handling and logging

3. ☁️ EVENT-DRIVEN TRIGGERS
   ├── S3 events trigger document processing
   ├── Automatic Lambda invocation
   ├── Event metadata passed as payload
   └── Asynchronous processing

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ERROR HANDLING & LOGGING                             │
└─────────────────────────────────────────────────────────────────────────────────┘

1. 🚨 ERROR PROPAGATION
   ├── Library Lambda errors returned to Business Logic
   ├── Business Logic handles and logs errors
   ├── Appropriate HTTP status codes returned
   └── Client receives meaningful error messages

2. 📊 LOGGING STRATEGY
   ├── Each Lambda logs its operations
   ├── CloudWatch Logs for debugging
   ├── Structured logging with context
   └── Performance metrics tracking

3. 🔄 RETRY MECHANISMS
   ├── Built-in Lambda retry for transient failures
   ├── Dead letter queues for failed invocations
   ├── Circuit breaker patterns for external services
   └── Graceful degradation when services unavailable
```

## 🎯 KEY ARCHITECTURAL PATTERNS

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ARCHITECTURE SUMMARY                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

📦 ZIP LAMBDAS (Business Logic)
├── Lightweight, fast cold starts
├── Direct AWS service access
├── Orchestrate complex workflows
├── Handle business rules and validation
└── Viewable source code in AWS Console

🐳 DOCKER LAMBDAS (Library Functions)
├── Heavy ML/AI libraries and models
├── Complex dependencies and frameworks
├── Optimized for specific tasks
├── Reusable across multiple business flows
└── Encapsulated library functionality

🔄 INVOCATION FLOW
├── API Gateway → ZIP Lambda → Docker Lambda
├── Synchronous RequestResponse pattern
├── JSON payload communication
├── Error handling and propagation
└── Logging and monitoring at each layer

💡 BENEFITS
├── Separation of concerns
├── Independent scaling
├── Code visibility vs. library encapsulation
├── Cost optimization
└── Maintainability and debugging
```
