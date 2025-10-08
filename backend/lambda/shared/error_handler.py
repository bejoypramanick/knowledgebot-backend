"""
Shared error handling utilities for microservices
"""
import json
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import time

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Error classification types"""
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
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorContext:
    """Error context information"""
    error_type: ErrorType
    severity: ErrorSeverity
    service_name: str
    operation: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    request_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    is_retryable: bool = True
    error_code: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class ChatbotError(Exception):
    """Base exception for chatbot services"""
    def __init__(self, message: str, error_context: ErrorContext):
        super().__init__(message)
        self.error_context = error_context
        self.message = message

class ValidationError(ChatbotError):
    """Validation error"""
    pass

class ExternalServiceError(ChatbotError):
    """External service error"""
    pass

class DatabaseError(ChatbotError):
    """Database error"""
    pass

class AIServiceError(ChatbotError):
    """AI service error"""
    pass

class ErrorHandler:
    """Centralized error handling for microservices"""
    
    @staticmethod
    def classify_error(exception: Exception, service_name: str, operation: str) -> ErrorContext:
        """Classify error and determine context"""
        error_type = ErrorType.UNKNOWN_ERROR
        severity = ErrorSeverity.MEDIUM
        is_retryable = True
        error_code = None
        
        # Classify by exception type
        if isinstance(exception, ValueError) or isinstance(exception, TypeError):
            error_type = ErrorType.VALIDATION_ERROR
            severity = ErrorSeverity.LOW
            is_retryable = False
        elif isinstance(exception, PermissionError):
            error_type = ErrorType.AUTHORIZATION_ERROR
            severity = ErrorSeverity.HIGH
            is_retryable = False
        elif isinstance(exception, FileNotFoundError):
            error_type = ErrorType.NOT_FOUND_ERROR
            severity = ErrorSeverity.MEDIUM
            is_retryable = False
        elif isinstance(exception, TimeoutError):
            error_type = ErrorType.TIMEOUT_ERROR
            severity = ErrorSeverity.MEDIUM
            is_retryable = True
        elif "boto3" in str(type(exception)) or "botocore" in str(type(exception)):
            if "AccessDenied" in str(exception):
                error_type = ErrorType.AUTHORIZATION_ERROR
                severity = ErrorSeverity.HIGH
                is_retryable = False
            elif "NoSuchBucket" in str(exception) or "NoSuchKey" in str(exception):
                error_type = ErrorType.NOT_FOUND_ERROR
                severity = ErrorSeverity.MEDIUM
                is_retryable = False
            else:
                error_type = ErrorType.STORAGE_ERROR
                severity = ErrorSeverity.MEDIUM
                is_retryable = True
        elif "anthropic" in str(type(exception)) or "claude" in str(exception).lower():
            error_type = ErrorType.AI_SERVICE_ERROR
            severity = ErrorSeverity.HIGH
            is_retryable = True
        elif "dynamodb" in str(type(exception)) or "dynamo" in str(exception).lower():
            error_type = ErrorType.DATABASE_ERROR
            severity = ErrorSeverity.MEDIUM
            is_retryable = True
        
        # Classify by error message patterns
        error_message = str(exception).lower()
        if "rate limit" in error_message or "throttle" in error_message:
            error_type = ErrorType.RATE_LIMIT_ERROR
            severity = ErrorSeverity.MEDIUM
            is_retryable = True
        elif "timeout" in error_message:
            error_type = ErrorType.TIMEOUT_ERROR
            severity = ErrorSeverity.MEDIUM
            is_retryable = True
        elif "not found" in error_message or "does not exist" in error_message:
            error_type = ErrorType.NOT_FOUND_ERROR
            severity = ErrorSeverity.LOW
            is_retryable = False
        elif "unauthorized" in error_message or "forbidden" in error_message:
            error_type = ErrorType.AUTHORIZATION_ERROR
            severity = ErrorSeverity.HIGH
            is_retryable = False
        
        return ErrorContext(
            error_type=error_type,
            severity=severity,
            service_name=service_name,
            operation=operation,
            is_retryable=is_retryable,
            error_code=error_code
        )
    
    @staticmethod
    def create_error_response(error_context: ErrorContext, message: str, status_code: int = 500) -> Dict[str, Any]:
        """Create standardized error response"""
        response = {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': error_context.error_type.value,
                'message': message,
                'error_code': error_context.error_code,
                'severity': error_context.severity.value,
                'service': error_context.service_name,
                'operation': error_context.operation,
                'retryable': error_context.is_retryable,
                'retry_count': error_context.retry_count,
                'timestamp': time.time()
            })
        }
        
        # Add additional data if available
        if error_context.additional_data:
            response['body'] = json.loads(response['body'])
            response['body']['additional_data'] = error_context.additional_data
            response['body'] = json.dumps(response['body'])
        
        return response
    
    @staticmethod
    def log_error(error_context: ErrorContext, exception: Exception, additional_data: Optional[Dict[str, Any]] = None):
        """Log error with proper context"""
        log_data = {
            'error_type': error_context.error_type.value,
            'severity': error_context.severity.value,
            'service': error_context.service_name,
            'operation': error_context.operation,
            'error_message': str(exception),
            'exception_type': type(exception).__name__,
            'retry_count': error_context.retry_count,
            'is_retryable': error_context.is_retryable
        }
        
        if additional_data:
            log_data.update(additional_data)
        
        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {log_data}")
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {log_data}")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {log_data}")
        else:
            logger.info(f"Low severity error: {log_data}")
        
        # Log full traceback for debugging
        logger.debug(f"Full traceback: {traceback.format_exc()}")

def error_handler(service_name: str, operation: str):
    """Decorator for error handling in lambda functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ChatbotError as e:
                # Re-raise custom errors with context
                ErrorHandler.log_error(e.error_context, e)
                return ErrorHandler.create_error_response(
                    e.error_context, 
                    e.message,
                    status_code=400 if e.error_context.error_type == ErrorType.VALIDATION_ERROR else 500
                )
            except Exception as e:
                # Classify and handle unknown errors
                error_context = ErrorHandler.classify_error(e, service_name, operation)
                ErrorHandler.log_error(error_context, e)
                
                status_code = 400 if error_context.error_type == ErrorType.VALIDATION_ERROR else 500
                return ErrorHandler.create_error_response(error_context, str(e), status_code)
        
        return wrapper
    return decorator

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    # Check if error is retryable
                    error_context = ErrorHandler.classify_error(e, "retry_handler", func.__name__)
                    if not error_context.is_retryable:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"Retry attempt {attempt + 1}/{max_retries} after {delay}s delay. Error: {str(e)}")
                    time.sleep(delay)
            
            # If all retries failed, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

# Global circuit breakers for external services
claude_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
dynamodb_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
s3_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
