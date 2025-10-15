#!/usr/bin/env python3
"""
Centralized Error Logger Lambda
Collects and aggregates error logs from all other Lambda functions

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
from typing import Dict, Any, List
import hashlib

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch_logs = boto3.client('logs')
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Configuration
ERROR_LOG_GROUP = '/aws/lambda/error-aggregator'
ERROR_TABLE = 'knowledgebot-error-logs'
ERROR_BUCKET = 'knowledgebot-error-logs'

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Centralized error logger handler with comprehensive logging and error handling
    
    Expected event format:
    {
        "source_lambda": "chat-orchestrator-websocket",
        "error_type": "TimeoutError",
        "error_message": "Operation timed out",
        "stack_trace": "Traceback...",
        "request_id": "abc123",
        "user_id": "user123",
        "additional_context": {...},
        "severity": "ERROR" | "WARNING" | "CRITICAL"
    }
    """
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== ERROR LOGGER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Validate event structure
        if not event or not isinstance(event, dict):
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = "Event must be a non-empty dictionary"
            logger.error(f"❌ Validation error: {error_msg}")
            
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Extract error information with validation
        source_lambda = event.get('source_lambda', 'unknown')
        error_type = event.get('error_type', 'UnknownError')
        error_message = event.get('error_message', 'No message provided')
        stack_trace = event.get('stack_trace', '')
        request_id = event.get('request_id', '')
        user_id = event.get('user_id', '')
        additional_context = event.get('additional_context', {})
        severity = event.get('severity', 'ERROR')
        
        logger.info(f"📊 Source Lambda: {source_lambda}")
        logger.info(f"📊 Error Type: {error_type}")
        logger.info(f"📊 Error Message: {error_message[:200]}{'...' if len(error_message) > 200 else ''}")
        logger.info(f"📊 Severity: {severity}")
        logger.info(f"📊 Request ID: {request_id}")
        logger.info(f"📊 User ID: {user_id}")
        logger.info(f"📊 Additional Context: {json.dumps(additional_context, default=str)[:200]}{'...' if len(json.dumps(additional_context, default=str)) > 200 else ''}")
        
        # Validate severity
        valid_severities = ['ERROR', 'WARNING', 'CRITICAL', 'INFO']
        if severity not in valid_severities:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Invalid severity: {severity}. Valid severities: {valid_severities}"
            logger.error(f"❌ Validation error: {error_msg}")
            
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Generate unique error ID
        try:
            error_id = generate_error_id(source_lambda, error_type, error_message, request_id)
            logger.info(f"📊 Generated Error ID: {error_id}")
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Failed to generate error ID: {str(e)}"
            logger.error(f"❌ Error ID generation failed: {error_msg}")
            
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Create error log entry
        error_log = {
            'error_id': error_id,
            'timestamp': datetime.now().isoformat(),
            'source_lambda': source_lambda,
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace,
            'request_id': request_id,
            'user_id': user_id,
            'severity': severity,
            'additional_context': additional_context,
            'ttl': int(datetime.now().timestamp()) + (30 * 24 * 60 * 60)  # 30 days TTL
        }
        
        logger.info(f"📊 Error log entry created: {error_id}")
        
        # Store in DynamoDB for querying
        try:
            dynamodb_success = store_error_in_dynamodb(error_log)
            if not dynamodb_success:
                logger.warning(f"⚠️ Failed to store error in DynamoDB: {error_id}")
        except Exception as e:
            logger.error(f"❌ Exception storing error in DynamoDB: {e}")
            logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        # Store in CloudWatch Logs for monitoring
        try:
            cloudwatch_success = store_error_in_cloudwatch(error_log)
            if not cloudwatch_success:
                logger.warning(f"⚠️ Failed to store error in CloudWatch: {error_id}")
        except Exception as e:
            logger.error(f"❌ Exception storing error in CloudWatch: {e}")
            logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        # Log critical errors prominently in CloudWatch
        if severity == 'CRITICAL':
            try:
                logger.info(f"🚨 Processing CRITICAL error: {error_id}")
                critical_success = log_critical_error_to_cloudwatch(error_log)
                if not critical_success:
                    logger.warning(f"⚠️ Failed to log critical error to CloudWatch: {error_id}")
                
                # Store in S3 for long-term storage
                s3_success = store_error_in_s3(error_log)
                if not s3_success:
                    logger.warning(f"⚠️ Failed to store critical error in S3: {error_id}")
            except Exception as e:
                logger.error(f"❌ Exception processing critical error: {e}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Error logged successfully: {error_id}")
        logger.info(f"📊 Processing time: {processing_time:.3f}s")
        logger.info(f"📊 Severity: {severity}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "error_id": error_id,
                "message": "Error logged successfully",
                "request_id": request_id,
                "processing_time": processing_time
            })
        }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error in error logger: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            })
        }

def generate_error_id(source_lambda: str, error_type: str, error_message: str, request_id: str) -> str:
    """Generate unique error ID"""
    content = f"{source_lambda}_{error_type}_{error_message}_{request_id}_{datetime.now().isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:16]

def store_error_in_dynamodb(error_log: Dict[str, Any]) -> bool:
    """Store error in DynamoDB for quick querying"""
    try:
        table = dynamodb.Table(ERROR_TABLE)
        table.put_item(Item=error_log)
        logger.info(f"✅ Error stored in DynamoDB: {error_log['error_id']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to store error in DynamoDB: {e}")
        return False

def store_error_in_cloudwatch(error_log: Dict[str, Any]) -> bool:
    """Store error in CloudWatch Logs"""
    try:
        log_stream_name = f"error-stream-{datetime.now().strftime('%Y-%m-%d')}"
        
        # Create log stream if it doesn't exist
        try:
            cloudwatch_logs.create_log_stream(
                logGroupName=ERROR_LOG_GROUP,
                logStreamName=log_stream_name
            )
        except cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
            pass
        
        # Create log event
        log_event = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'message': json.dumps(error_log, default=str)
        }
        
        # Put log event
        cloudwatch_logs.put_log_events(
            logGroupName=ERROR_LOG_GROUP,
            logStreamName=log_stream_name,
            logEvents=[log_event]
        )
        
        logger.info(f"✅ Error stored in CloudWatch: {error_log['error_id']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to store error in CloudWatch: {e}")
        return False

def store_error_in_s3(error_log: Dict[str, Any]) -> bool:
    """Store critical errors in S3 for long-term storage"""
    try:
        key = f"critical-errors/{datetime.now().strftime('%Y/%m/%d')}/{error_log['error_id']}.json"
        
        s3_client.put_object(
            Bucket=ERROR_BUCKET,
            Key=key,
            Body=json.dumps(error_log, indent=2, default=str),
            ContentType='application/json'
        )
        
        logger.info(f"✅ Critical error stored in S3: {key}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to store error in S3: {e}")
        return False

def log_critical_error_to_cloudwatch(error_log: Dict[str, Any]) -> bool:
    """Log critical errors prominently in CloudWatch"""
    try:
        # Log critical errors with high visibility
        logger.critical(f"🚨 CRITICAL ERROR: {error_log['error_id']}")
        logger.critical(f"Source: {error_log['source_lambda']}")
        logger.critical(f"Type: {error_log['error_type']}")
        logger.critical(f"Message: {error_log['error_message']}")
        logger.critical(f"Request ID: {error_log['request_id']}")
        logger.critical(f"User ID: {error_log['user_id']}")
        logger.critical(f"Timestamp: {error_log['timestamp']}")
        logger.critical(f"Stack Trace: {error_log['stack_trace']}")
        logger.critical(f"Additional Context: {json.dumps(error_log['additional_context'], indent=2)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to log critical error to CloudWatch: {e}")
        return False

def get_error_summary(hours: int = 24) -> Dict[str, Any]:
    """Get error summary for the last N hours"""
    try:
        table = dynamodb.Table(ERROR_TABLE)
        
        # Calculate timestamp threshold
        threshold = int(datetime.now().timestamp()) - (hours * 60 * 60)
        
        # Query errors
        response = table.scan(
            FilterExpression='timestamp > :threshold',
            ExpressionAttributeValues={':threshold': threshold}
        )
        
        errors = response.get('Items', [])
        
        # Group by source lambda
        by_source = {}
        by_severity = {}
        by_error_type = {}
        
        for error in errors:
            source = error.get('source_lambda', 'unknown')
            severity = error.get('severity', 'ERROR')
            error_type = error.get('error_type', 'UnknownError')
            
            by_source[source] = by_source.get(source, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_error_type[error_type] = by_error_type.get(error_type, 0) + 1
        
        return {
            'total_errors': len(errors),
            'time_period_hours': hours,
            'by_source_lambda': by_source,
            'by_severity': by_severity,
            'by_error_type': by_error_type,
            'recent_errors': errors[-10:]  # Last 10 errors
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get error summary: {e}")
        return {'error': str(e)}

# Utility function for other Lambdas to use
def log_error(source_lambda: str, error: Exception, context: Any = None, 
              additional_context: Dict[str, Any] = None, severity: str = 'ERROR') -> str:
    """
    Utility function for other Lambdas to log errors
    
    Usage:
    from error_logger_handler import log_error
    try:
        # some operation
        pass
    except Exception as e:
        error_id = log_error('my-lambda', e, context, {'user_id': '123'}, 'ERROR')
    """
    try:
        # Prepare error data
        error_data = {
            'source_lambda': source_lambda,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'stack_trace': traceback.format_exc(),
            'request_id': context.aws_request_id if context else '',
            'user_id': additional_context.get('user_id', '') if additional_context else '',
            'additional_context': additional_context or {},
            'severity': severity
        }
        
        # Invoke error logger Lambda
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
            FunctionName='error-logger-handler',
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(error_data)
        )
        
        return error_data.get('error_id', 'unknown')
        
    except Exception as e:
        logger.error(f"❌ Failed to log error: {e}")
        return 'logging_failed'
