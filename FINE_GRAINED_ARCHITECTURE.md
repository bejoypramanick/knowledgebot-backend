# Fine-Grained Microservices Architecture

This document outlines the ultra-fine-grained microservices architecture with comprehensive error handling, retry mechanisms, and circuit breakers.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │───▶│  API Gateway     │───▶│  Orchestrator   │
│   (React)       │    │                  │    │  Lambda         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                       ┌─────────────────────────────────────────┐
                       │        Fine-Grained Services            │
                       │                                         │
                       │  ┌─────────────┐  ┌─────────────────┐  │
                       │  │Claude       │  │Action Executor  │  │
                       │  │Decision     │  │Lambda           │  │
                       │  └─────────────┘  └─────────────────┘  │
                       │                                         │
                       │  ┌─────────────┐  ┌─────────────────┐  │
                       │  │Embedding    │  │Vector Search    │  │
                       │  │Service      │  │Lambda           │  │
                       │  └─────────────┘  └─────────────────┘  │
                       │                                         │
                       │  ┌─────────────┐  ┌─────────────────┐  │
                       │  │Document     │  │Document         │  │
                       │  │Metadata     │  │Content          │  │
                       │  │Lambda       │  │Lambda           │  │
                       │  └─────────────┘  └─────────────────┘  │
                       │                                         │
                       │  ┌─────────────┐  ┌─────────────────┐  │
                       │  │Source       │  │Response         │  │
                       │  │Extractor    │  │Formatter        │  │
                       │  │Lambda       │  │Lambda           │  │
                       │  └─────────────┘  └─────────────────┘  │
                       │                                         │
                       │  ┌─────────────────────────────────┐  │
                       │  │Conversation Manager Lambda      │  │
                       │  └─────────────────────────────────┘  │
                       └─────────────────────────────────────────┘
```

## Microservices Breakdown

### 1. **Claude Decision Lambda** (`chatbot-claude-decision`)
- **Single Responsibility**: Pure AI decision making using Claude
- **Input**: User message, conversation history
- **Output**: Action plan with detailed instructions
- **Error Handling**: 
  - Rate limit handling with fallback responses
  - API key validation
  - Response parsing with fallback plans
  - Conversation history retrieval errors

### 2. **Action Executor Lambda** (`chatbot-action-executor`)
- **Single Responsibility**: Execute planned actions by calling other services
- **Input**: List of actions, execution type (parallel/sequential)
- **Output**: Results from all executed actions
- **Error Handling**:
  - Retry logic with exponential backoff
  - Circuit breakers for external services
  - Individual action failure isolation
  - Timeout handling

### 3. **Embedding Service Lambda** (`chatbot-embedding-service`)
- **Single Responsibility**: Generate embeddings using sentence-transformers
- **Input**: Text to embed
- **Output**: Vector embeddings
- **Error Handling**:
  - Model loading failures
  - Memory management for large texts
  - Embedding generation errors

### 4. **Vector Search Lambda** (`chatbot-vector-search`)
- **Single Responsibility**: Perform similarity search using embeddings
- **Input**: Query embedding, search parameters
- **Output**: Similar chunks with scores
- **Error Handling**:
  - Database connection failures
  - Vector calculation errors
  - Result ranking issues

### 5. **Document Metadata Lambda** (`chatbot-document-metadata`)
- **Single Responsibility**: Handle document metadata operations
- **Input**: Document queries, filters
- **Output**: Document metadata lists
- **Error Handling**:
  - Database query failures
  - Invalid filter parameters
  - Pagination errors

### 6. **Document Content Lambda** (`chatbot-document-content`)
- **Single Responsibility**: Retrieve document content and structure
- **Input**: Document ID, content type
- **Output**: Document content with hierarchy
- **Error Handling**:
  - Document not found
  - Content parsing errors
  - Access permission issues

### 7. **Source Extractor Lambda** (`chatbot-source-extractor`)
- **Single Responsibility**: Extract and format sources from action results
- **Input**: Raw action results
- **Output**: Formatted source metadata
- **Error Handling**:
  - Malformed result data
  - Missing source information
  - Formatting errors

### 8. **Response Formatter Lambda** (`chatbot-response-formatter`)
- **Single Responsibility**: Format final response with sources
- **Input**: AI response, sources, metadata
- **Output**: Formatted response with proper structure
- **Error Handling**:
  - Response validation errors
  - Source formatting issues
  - Output structure problems

### 9. **Conversation Manager Lambda** (`chatbot-conversation-manager`)
- **Single Responsibility**: Handle conversation CRUD operations
- **Input**: Conversation data, user messages
- **Output**: Conversation state, history
- **Error Handling**:
  - Database write failures
  - Conversation not found
  - Data validation errors

## Error Handling Architecture

### Error Classification System
```python
class ErrorType(Enum):
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TIMEOUT_ERROR = "timeout_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    DATABASE_ERROR = "database_error"
    STORAGE_ERROR = "storage_error"
    AI_SERVICE_ERROR = "ai_service_error"
    CONFIGURATION_ERROR = "configuration_error"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

### Retry Mechanisms
- **Exponential Backoff**: Base delay increases exponentially with each retry
- **Max Retries**: Configurable per service (3-5 retries)
- **Retryable Error Detection**: Automatic classification of retryable errors
- **Circuit Breakers**: Prevent cascading failures

### Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
```

### Error Response Format
```json
{
  "error": "error_type",
  "message": "Human readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "severity": "low|medium|high|critical",
  "service": "service_name",
  "operation": "operation_name",
  "retryable": true,
  "retry_count": 2,
  "timestamp": 1640995200.0,
  "additional_data": {
    "conversation_id": "conv-123",
    "request_id": "req-456"
  }
}
```

## Benefits of Fine-Grained Architecture

### 1. **Ultra-Specific Responsibilities**
- Each lambda has exactly one job
- Easier to test and debug
- Clear ownership and maintenance

### 2. **Independent Scaling**
- Scale only what's needed
- Different memory/timeout per service
- Cost optimization

### 3. **Fault Isolation**
- Service failures don't cascade
- Graceful degradation
- Partial functionality maintained

### 4. **Development Velocity**
- Teams can work independently
- Faster deployment cycles
- Easier feature additions

### 5. **Comprehensive Error Handling**
- Detailed error classification
- Automatic retry mechanisms
- Circuit breaker protection
- Graceful fallbacks

### 6. **Monitoring & Observability**
- Per-service metrics
- Detailed error tracking
- Performance monitoring
- Debugging capabilities

## Deployment Strategy

### GitHub Actions Workflow
- **Trigger**: Push to main branch
- **Build**: Docker images for each service
- **Deploy**: ECR push and Lambda update
- **Test**: Automated testing pipeline
- **Monitor**: Health checks and alerts

### Environment Configuration
```yaml
Environment Variables:
  - CLAUDE_API_KEY (secrets)
  - AWS_REGION: ap-south-1
  - LOG_LEVEL: INFO
  - MAX_RETRIES: 3
  - CIRCUIT_BREAKER_THRESHOLD: 5
```

## Monitoring & Alerting

### CloudWatch Metrics
- **Invocation Count**: Per service
- **Error Rate**: By error type
- **Duration**: P50, P95, P99
- **Throttles**: Rate limiting
- **Circuit Breaker State**: Open/Closed

### Alerts
- **High Error Rate**: >5% errors
- **Circuit Breaker Open**: Service unavailable
- **High Latency**: >30s response time
- **Memory Usage**: >80% utilization

## Testing Strategy

### Unit Tests
- Individual service testing
- Error scenario coverage
- Mock external dependencies

### Integration Tests
- Service-to-service communication
- End-to-end workflows
- Error propagation testing

### Load Tests
- Concurrent request handling
- Circuit breaker behavior
- Retry mechanism validation

## Cost Optimization

### Resource Allocation
- **Claude Decision**: 1024MB (AI processing)
- **Action Executor**: 512MB (coordination)
- **Embedding Service**: 2048MB (ML model)
- **Vector Search**: 1024MB (computation)
- **Document Services**: 256MB (simple operations)
- **Response Services**: 512MB (formatting)

### Cold Start Mitigation
- Provisioned concurrency for critical services
- Container reuse strategies
- Optimized dependencies

This fine-grained architecture provides maximum flexibility, reliability, and maintainability while ensuring comprehensive error handling and monitoring capabilities.
