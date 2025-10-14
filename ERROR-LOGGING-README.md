# Centralized Error Logging System

A comprehensive error logging system for KnowledgeBot that centralizes error collection from all Lambda functions and provides monitoring through CloudWatch.

## 🎯 Overview

This system provides:
- **Centralized error collection** from all Lambda functions
- **CloudWatch monitoring** with dashboards and alarms
- **DynamoDB storage** for error querying and analytics
- **Simple integration** with existing Lambda functions

## 🏗️ Architecture

```
Lambda Functions → Error Logger → CloudWatch Logs + DynamoDB
                                    ↓
                              CloudWatch Dashboard
                                    ↓
                              CloudWatch Alarms
```

## 📁 Components

### Core Files
- `microservices/error-logger-handler.py` - Central error collection Lambda
- `microservices/error-query-handler.py` - API for querying errors
- `utils/error_logger.py` - Utility for other Lambda functions
- `error-logging-infrastructure.yml` - CloudFormation template

### GitHub Actions
- `.github/workflows/deploy-error-logging.yml` - Deploy infrastructure
- `.github/workflows/update-lambda-error-logging.yml` - Update Lambda functions
- `.github/workflows/test-error-logging.yml` - Test the system

### Monitoring
- `cloudwatch-dashboard.json` - CloudWatch dashboard configuration

## 🚀 Quick Start

### 1. Deploy Infrastructure
```bash
# Deploy via GitHub Actions (recommended)
# Or manually:
aws cloudformation deploy \
  --template-file error-logging-infrastructure.yml \
  --stack-name knowledgebot-error-logging-prod \
  --capabilities CAPABILITY_IAM
```

### 2. Update Lambda Functions
```python
# In your Lambda function
from error_logger import log_error, log_timeout_error

try:
    # Your code
    pass
except Exception as e:
    log_error('my-lambda', e, context)
```

### 3. Monitor Errors
- **CloudWatch Dashboard**: `KnowledgeBot-Error-Monitoring-prod`
- **CloudWatch Logs**: `/aws/lambda/prod-error-logger`
- **DynamoDB Table**: `prod-knowledgebot-error-logs`

## 📊 Error Data Structure

```json
{
  "error_id": "abc123def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "source_lambda": "chat-orchestrator-websocket",
  "error_type": "TimeoutError",
  "error_message": "Operation timed out",
  "stack_trace": "Traceback...",
  "request_id": "req-123",
  "user_id": "user-456",
  "severity": "ERROR",
  "additional_context": {
    "connection_id": "conn-789",
    "query": "What is AI?"
  }
}
```

## 🔧 Usage Examples

### Basic Error Logging
```python
from error_logger import log_error

try:
    # Your code
    pass
except Exception as e:
    log_error('my-lambda', e, context)
```

### Timeout Error Logging
```python
from error_logger import log_timeout_error

try:
    # Long operation
    pass
except TimeoutError:
    log_timeout_error('my-lambda', 'data_processing', context)
```

### Service Failure Logging
```python
from error_logger import log_service_failure

try:
    # External API call
    pass
except Exception as e:
    log_service_failure('my-lambda', 'external-api', str(e), context)
```

### Custom Error Logging
```python
from error_logger import log_custom_error

log_custom_error(
    'my-lambda',
    'ValidationError',
    'Email is required',
    context,
    {'user_id': '123'},
    'WARNING'
)
```

## 📈 Monitoring

### CloudWatch Dashboard
The dashboard shows:
- **Error rates** over time
- **Recent errors** from all Lambda functions
- **Critical errors** prominently displayed
- **Errors by Lambda function** breakdown

### CloudWatch Alarms
- **High Error Rate**: Triggers when >5 errors in 5 minutes
- **Critical Errors**: Triggers on any critical error

### Error Query API
```bash
# Get error summary
GET /errors/summary?hours=24

# Get specific errors
GET /errors?source_lambda=chat-orchestrator&severity=ERROR&limit=10
```

## 💰 Cost Optimization

- **DynamoDB TTL**: 30 days automatic cleanup
- **CloudWatch Logs**: 14 days retention
- **S3 Lifecycle**: 30 days for critical errors only
- **Reduced thresholds**: Lower alarm thresholds to reduce noise

## 🔍 Troubleshooting

### Common Issues

1. **Errors not appearing in CloudWatch**
   - Check Lambda function permissions
   - Verify error logger function is deployed
   - Check CloudWatch log group exists

2. **High costs**
   - Reduce DynamoDB TTL
   - Decrease CloudWatch log retention
   - Filter out non-critical errors

3. **Missing errors**
   - Ensure all Lambda functions import error_logger
   - Check error logger function logs
   - Verify DynamoDB table permissions

### Debug Commands
```bash
# Check error logger function
aws lambda invoke --function-name prod-error-logger response.json

# Query recent errors
aws dynamodb scan --table-name prod-knowledgebot-error-logs --max-items 5

# Check CloudWatch logs
aws logs describe-log-streams --log-group-name /aws/lambda/prod-error-logger
```

## 🎯 Benefits

✅ **Centralized monitoring** - All errors in one place  
✅ **CloudWatch integration** - Native AWS monitoring  
✅ **Cost effective** - Optimized storage and retention  
✅ **Easy integration** - Simple import and function calls  
✅ **Real-time alerts** - CloudWatch alarms for critical issues  
✅ **Error analytics** - Trends and patterns via API  
✅ **Scalable** - Handles high error volumes  

## 📝 Notes

- Errors are logged asynchronously to avoid blocking main execution
- Critical errors are logged prominently in CloudWatch for visibility
- The system is designed to be cost-effective with automatic cleanup
- All monitoring is done through CloudWatch - no external services needed
