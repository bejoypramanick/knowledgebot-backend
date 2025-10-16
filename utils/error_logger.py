#!/usr/bin/env python3
"""
Error Logging Utility for KnowledgeBot Backend
Centralized error logging and monitoring system
"""

import json
import logging
import traceback
import boto3
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ErrorLogger:
    """Centralized error logging system"""
    
    def __init__(self):
        self.cloudwatch_client = None
        self.log_group_name = os.getenv('LOG_GROUP_NAME', 'knowledgebot-errors')
        self.log_stream_name = os.getenv('LOG_STREAM_NAME', 'error-stream')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize CloudWatch client if AWS credentials are available
        try:
            self.cloudwatch_client = boto3.client('logs', region_name=self.region)
            self._ensure_log_group_exists()
        except Exception as e:
            logger.warning(f"Could not initialize CloudWatch client: {e}")
            self.cloudwatch_client = None
    
    def _ensure_log_group_exists(self):
        """Ensure the CloudWatch log group exists"""
        try:
            self.cloudwatch_client.describe_log_groups(
                logGroupNamePrefix=self.log_group_name
            )
        except self.cloudwatch_client.exceptions.ResourceNotFoundException:
            try:
                self.cloudwatch_client.create_log_group(logGroupName=self.log_group_name)
                logger.info(f"Created log group: {self.log_group_name}")
            except Exception as e:
                logger.error(f"Failed to create log group: {e}")
    
    def _log_to_cloudwatch(self, message: str, level: str = "ERROR"):
        """Log message to CloudWatch"""
        if not self.cloudwatch_client:
            return
        
        try:
            timestamp = int(datetime.now().timestamp() * 1000)
            
            # Ensure log stream exists
            try:
                self.cloudwatch_client.describe_log_streams(
                    logGroupName=self.log_group_name,
                    logStreamNamePrefix=self.log_stream_name
                )
            except self.cloudwatch_client.exceptions.ResourceNotFoundException:
                self.cloudwatch_client.create_log_stream(
                    logGroupName=self.log_group_name,
                    logStreamName=self.log_stream_name
                )
            
            # Put log event
            self.cloudwatch_client.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': message
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to log to CloudWatch: {e}")
    
    def _format_error_message(self, service: str, error: Exception, context: Any, 
                            metadata: Dict[str, Any], level: str) -> str:
        """Format error message for logging"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "level": level,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": str(context) if context else None,
            "metadata": metadata
        }
        return json.dumps(error_data, indent=2)
    
    def log_error(self, service: str, error: Exception, context: Any, 
                  metadata: Dict[str, Any], level: str = "ERROR"):
        """Log an error with full context"""
        try:
            message = self._format_error_message(service, error, context, metadata, level)
            
            # Log to local logger
            if level == "ERROR":
                logger.error(message)
            elif level == "WARNING":
                logger.warning(message)
            else:
                logger.info(message)
            
            # Log to CloudWatch
            self._log_to_cloudwatch(message, level)
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def log_custom_error(self, service: str, error_type: str, metadata: Dict[str, Any], 
                        level: str = "ERROR"):
        """Log a custom error without an exception object"""
        try:
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "service": service,
                "level": level,
                "error_type": error_type,
                "metadata": metadata
            }
            message = json.dumps(error_data, indent=2)
            
            # Log to local logger
            if level == "ERROR":
                logger.error(message)
            elif level == "WARNING":
                logger.warning(message)
            else:
                logger.info(message)
            
            # Log to CloudWatch
            self._log_to_cloudwatch(message, level)
            
        except Exception as e:
            logger.error(f"Failed to log custom error: {e}")
    
    def log_service_failure(self, service: str, reason: str, metadata: Dict[str, Any], 
                           level: str = "ERROR"):
        """Log a service failure"""
        try:
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "service": service,
                "level": level,
                "error_type": "ServiceFailure",
                "reason": reason,
                "metadata": metadata
            }
            message = json.dumps(error_data, indent=2)
            
            # Log to local logger
            if level == "ERROR":
                logger.error(message)
            elif level == "WARNING":
                logger.warning(message)
            else:
                logger.info(message)
            
            # Log to CloudWatch
            self._log_to_cloudwatch(message, level)
            
        except Exception as e:
            logger.error(f"Failed to log service failure: {e}")

# Global error logger instance
_error_logger = ErrorLogger()

def log_error(service: str, error: Exception, context: Any, 
              metadata: Dict[str, Any], level: str = "ERROR"):
    """Log an error with full context"""
    _error_logger.log_error(service, error, context, metadata, level)

def log_custom_error(service: str, error_type: str, metadata: Dict[str, Any], 
                    level: str = "ERROR"):
    """Log a custom error without an exception object"""
    _error_logger.log_custom_error(service, error_type, metadata, level)

def log_service_failure(service: str, reason: str, metadata: Dict[str, Any], 
                       level: str = "ERROR"):
    """Log a service failure"""
    _error_logger.log_service_failure(service, reason, metadata, level)

