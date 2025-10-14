"""
Error Logger Utility
Easy-to-use error logging for all Lambda functions

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

import json
import logging
import boto3
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ErrorLogger:
    """Centralized error logging utility"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.error_logger_function = os.environ.get('ERROR_LOGGER_FUNCTION', 'error-logger-handler')
    
    def log_error(self, source_lambda: str, error: Exception, context: Any = None, 
                  additional_context: Dict[str, Any] = None, severity: str = 'ERROR') -> str:
        """
        Log an error to the centralized error logger
        
        Args:
            source_lambda: Name of the Lambda function where error occurred
            error: The exception that occurred
            context: Lambda context object
            additional_context: Additional context data
            severity: Error severity (ERROR, WARNING, CRITICAL)
        
        Returns:
            Error ID for tracking
        """
        try:
            # Generate error ID
            error_id = self._generate_error_id(source_lambda, error, context)
            
            # Prepare error data
            error_data = {
                'source_lambda': source_lambda,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'stack_trace': traceback.format_exc(),
                'request_id': context.aws_request_id if context else '',
                'user_id': additional_context.get('user_id', '') if additional_context else '',
                'additional_context': additional_context or {},
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            }
            
            # Invoke error logger Lambda asynchronously
            self.lambda_client.invoke(
                FunctionName=self.error_logger_function,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(error_data)
            )
            
            logger.info(f"✅ Error logged: {error_id}")
            return error_id
            
        except Exception as e:
            logger.error(f"❌ Failed to log error: {e}")
            return 'logging_failed'
    
    def log_custom_error(self, source_lambda: str, error_type: str, error_message: str,
                        context: Any = None, additional_context: Dict[str, Any] = None,
                        severity: str = 'ERROR') -> str:
        """
        Log a custom error (not an exception)
        
        Args:
            source_lambda: Name of the Lambda function
            error_type: Type of error
            error_message: Error message
            context: Lambda context object
            additional_context: Additional context data
            severity: Error severity
        """
        try:
            error_data = {
                'source_lambda': source_lambda,
                'error_type': error_type,
                'error_message': error_message,
                'stack_trace': '',
                'request_id': context.aws_request_id if context else '',
                'user_id': additional_context.get('user_id', '') if additional_context else '',
                'additional_context': additional_context or {},
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            }
            
            self.lambda_client.invoke(
                FunctionName=self.error_logger_function,
                InvocationType='Event',
                Payload=json.dumps(error_data)
            )
            
            error_id = self._generate_error_id(source_lambda, error_type, context)
            logger.info(f"✅ Custom error logged: {error_id}")
            return error_id
            
        except Exception as e:
            logger.error(f"❌ Failed to log custom error: {e}")
            return 'logging_failed'
    
    def _generate_error_id(self, source_lambda: str, error: Any, context: Any = None) -> str:
        """Generate unique error ID"""
        import hashlib
        content = f"{source_lambda}_{str(error)}_{context.aws_request_id if context else ''}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

# Global instance for easy importing
error_logger = ErrorLogger()

# Convenience functions
def log_error(source_lambda: str, error: Exception, context: Any = None, 
              additional_context: Dict[str, Any] = None, severity: str = 'ERROR') -> str:
    """Convenience function to log errors"""
    return error_logger.log_error(source_lambda, error, context, additional_context, severity)

def log_custom_error(source_lambda: str, error_type: str, error_message: str,
                    context: Any = None, additional_context: Dict[str, Any] = None,
                    severity: str = 'ERROR') -> str:
    """Convenience function to log custom errors"""
    return error_logger.log_custom_error(source_lambda, error_type, error_message, 
                                       context, additional_context, severity)

def log_timeout_error(source_lambda: str, operation: str, context: Any = None,
                     additional_context: Dict[str, Any] = None) -> str:
    """Convenience function to log timeout errors"""
    return error_logger.log_custom_error(
        source_lambda, 
        'TimeoutError', 
        f"Operation '{operation}' timed out",
        context, 
        additional_context, 
        'WARNING'
    )

def log_service_failure(source_lambda: str, service_name: str, error_message: str,
                       context: Any = None, additional_context: Dict[str, Any] = None) -> str:
    """Convenience function to log service failures"""
    return error_logger.log_custom_error(
        source_lambda,
        'ServiceFailure',
        f"{service_name} service failed: {error_message}",
        context,
        additional_context,
        'ERROR'
    )
