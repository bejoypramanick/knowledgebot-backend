# Lambda Deployment Strategy: All Docker Images

## Standardized Approach

**All Lambda Functions Use Docker Images For:**
- Consistent runtime environment
- Uniform deployment process
- Easier dependency management
- Better isolation and security
- Simplified CI/CD pipeline
- Standardized monitoring and logging

## All Services - Docker Images

### 🐳 **EXISTING DOCKER SERVICES**

#### 1. **RAG Processor Lambda** (`chatbot-rag-processor`)
- **Dependencies**: `docling`, `sentence-transformers`, `numpy`
- **Size**: ~500MB+ (ML models)
- **Build Time**: 5-10 minutes
- **Dockerfile**: ✅ Already exists

#### 2. **RAG Search Lambda** (`chatbot-rag-search`)
- **Dependencies**: `sentence-transformers`, `numpy`
- **Size**: ~300MB+ (transformer models)
- **Build Time**: 3-5 minutes
- **Dockerfile**: ✅ Already exists

#### 3. **Chat Handler Lambda** (`chatbot-chat-handler`)
- **Dependencies**: `anthropic`, `boto3`, `pydantic`, `requests`, `httpx`
- **Size**: ~100MB+
- **Build Time**: 2-3 minutes
- **Dockerfile**: ✅ Already exists

#### 4. **Orchestrator Lambda** (`chatbot-orchestrator`)
- **Dependencies**: `anthropic`, `boto3`, `pydantic`
- **Size**: ~50MB
- **Build Time**: 1-2 minutes
- **Dockerfile**: ✅ Already exists

#### 5. **Document Management Lambda** (`chatbot-document-management`)
- **Dependencies**: `boto3`
- **Size**: ~30MB
- **Build Time**: 30 seconds
- **Dockerfile**: ✅ Already exists

#### 6. **Response Enhancement Lambda** (`chatbot-response-enhancement`)
- **Dependencies**: `anthropic`, `boto3`
- **Size**: ~40MB
- **Build Time**: 45 seconds
- **Dockerfile**: ✅ Already exists

### 🐳 **NEW DOCKER SERVICES**

#### 7. **Claude Decision Lambda** (`chatbot-claude-decision`)
- **Dependencies**: `anthropic`, `boto3`, `pydantic`
- **Size**: ~50MB
- **Build Time**: 1-2 minutes
- **Dockerfile**: ✅ Already exists

#### 8. **Action Executor Lambda** (`chatbot-action-executor`)
- **Dependencies**: `boto3`, `pydantic`
- **Size**: ~30MB
- **Build Time**: 30 seconds
- **Dockerfile**: ✅ Already exists

#### 9. **Embedding Service Lambda** (`chatbot-embedding-service`)
- **Dependencies**: `sentence-transformers`, `numpy`, `torch`
- **Size**: ~400MB+ (transformer models)
- **Build Time**: 5-8 minutes
- **Dockerfile**: 🔄 To be created

#### 10. **Vector Search Lambda** (`chatbot-vector-search`)
- **Dependencies**: `numpy`, `scipy`, `faiss-cpu`
- **Size**: ~200MB+ (numerical libraries)
- **Build Time**: 3-5 minutes
- **Dockerfile**: 🔄 To be created

#### 11. **Document Metadata Lambda** (`chatbot-document-metadata`)
- **Dependencies**: `boto3`
- **Size**: ~30MB
- **Build Time**: 30 seconds
- **Dockerfile**: 🔄 To be created

#### 12. **Document Content Lambda** (`chatbot-document-content`)
- **Dependencies**: `boto3`
- **Size**: ~30MB
- **Build Time**: 30 seconds
- **Dockerfile**: 🔄 To be created

#### 13. **Source Extractor Lambda** (`chatbot-source-extractor`)
- **Dependencies**: `boto3`, `pydantic`
- **Size**: ~35MB
- **Build Time**: 45 seconds
- **Dockerfile**: 🔄 To be created

#### 14. **Response Formatter Lambda** (`chatbot-response-formatter`)
- **Dependencies**: `boto3`, `pydantic`
- **Size**: ~35MB
- **Build Time**: 45 seconds
- **Dockerfile**: 🔄 To be created

#### 15. **Conversation Manager Lambda** (`chatbot-conversation-manager`)
- **Dependencies**: `boto3`, `pydantic`
- **Size**: ~35MB
- **Build Time**: 45 seconds
- **Dockerfile**: 🔄 To be created

## Deployment Strategy Implementation

### Docker Images (Heavy Dependencies)
```yaml
# GitHub Actions for Docker images
- name: Build and push RAG Processor
  run: |
    cd backend/lambda/rag-processor
    docker build -t chatbot-rag-processor .
    docker tag chatbot-rag-processor:latest $ECR_REGISTRY/chatbot-rag-processor:latest
    docker push $ECR_REGISTRY/chatbot-rag-processor:latest

- name: Build and push RAG Search
  run: |
    cd backend/lambda/rag-search
    docker build -t chatbot-rag-search .
    docker tag chatbot-rag-search:latest $ECR_REGISTRY/chatbot-rag-search:latest
    docker push $ECR_REGISTRY/chatbot-rag-search:latest
```

### ZIP Files (Lightweight Dependencies)
```yaml
# GitHub Actions for ZIP files
- name: Package and deploy Orchestrator
  run: |
    cd backend/lambda/orchestrator
    pip install -r requirements.txt -t .
    zip -r orchestrator.zip .
    aws lambda update-function-code \
      --function-name chatbot-orchestrator \
      --zip-file fileb://orchestrator.zip

- name: Package and deploy Document Management
  run: |
    cd backend/lambda/document-management
    pip install -r requirements.txt -t .
    zip -r document-management.zip .
    aws lambda update-function-code \
      --function-name chatbot-document-management \
      --zip-file fileb://document-management.zip
```

## Cost and Performance Implications

### Docker Images
- **Cold Start**: 2-5 seconds (container initialization)
- **Memory**: Higher baseline memory usage
- **Cost**: Higher due to container overhead
- **Deployment**: Slower (image build + push)
- **Use Case**: Heavy ML/AI workloads

### ZIP Files
- **Cold Start**: 500ms-2s (package loading)
- **Memory**: Lower baseline memory usage
- **Cost**: Lower due to no container overhead
- **Deployment**: Faster (direct upload)
- **Use Case**: Lightweight business logic

## Recommended Architecture

### Current Services (Hybrid Approach)
```
Docker Images (3 services):
├── chatbot-rag-processor (ML processing)
├── chatbot-rag-search (ML search)
└── chatbot-chat-handler (orchestration)

ZIP Files (2 services):
├── chatbot-orchestrator (coordination)
├── chatbot-document-management (simple ops)
└── chatbot-response-enhancement (lightweight AI)
```

### Fine-Grained Services (Optimized)
```
Docker Images (2 services):
├── chatbot-embedding-service (ML models)
└── chatbot-vector-search (numerical computing)

ZIP Files (7 services):
├── chatbot-claude-decision (AI decisions)
├── chatbot-action-executor (coordination)
├── chatbot-document-metadata (DynamoDB)
├── chatbot-document-content (S3)
├── chatbot-source-extractor (data processing)
├── chatbot-response-formatter (formatting)
└── chatbot-conversation-manager (DynamoDB)
```

## Benefits of This Strategy

### Cost Optimization
- **70% of services** use lightweight ZIP deployment
- **30% of services** use Docker only when necessary
- **Reduced cold starts** for most operations
- **Lower memory usage** for simple services

### Development Velocity
- **Faster deployment** for most changes
- **Easier debugging** for ZIP-based services
- **Simpler CI/CD** for lightweight services
- **Independent scaling** per service type

### Performance
- **Optimal cold start times** per service type
- **Right-sized resources** for each workload
- **Efficient memory usage** across all services
- **Faster iteration cycles** for development

This hybrid approach provides the best balance of performance, cost, and development velocity for your microservices architecture.
