#!/usr/bin/env python3
"""
Error Query Handler Lambda
Provides API endpoints for querying and analyzing error logs

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

import json
import logging
import boto3
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Configuration
ERROR_TABLE = 'knowledgebot-error-logs'

# Error logging utility
def log_error(source_lambda: str, error: Exception, context: Any, 
              additional_data: Dict[str, Any] = None, severity: str = 'ERROR'):
    """Log error to centralized system"""
    try:
        error_data = {
            'source_lambda': source_lambda,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'request_id': context.aws_request_id if context else 'unknown',
            'additional_data': additional_data or {}
        }
        
        # Log to CloudWatch
        logger.error(f"❌ {source_lambda} Error: {error_data}")
        
        # Store in DynamoDB
        table = dynamodb.Table(ERROR_TABLE)
        table.put_item(Item=error_data)
        
    except Exception as e:
        logger.error(f"❌ Failed to log error: {e}")

def log_custom_error(source_lambda: str, error_message: str, 
                    additional_data: Dict[str, Any] = None, severity: str = 'ERROR'):
    """Log custom error message"""
    try:
        error_data = {
            'source_lambda': source_lambda,
            'error_type': 'CustomError',
            'error_message': error_message,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'additional_data': additional_data or {}
        }
        
        # Log to CloudWatch
        logger.error(f"❌ {source_lambda} Custom Error: {error_data}")
        
        # Store in DynamoDB
        table = dynamodb.Table(ERROR_TABLE)
        table.put_item(Item=error_data)
        
    except Exception as e:
        logger.error(f"❌ Failed to log custom error: {e}")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Error query handler for retrieving and analyzing error logs with comprehensive logging and error handling
    
    Query parameters:
    - hours: Number of hours to look back (default: 24)
    - source_lambda: Filter by source Lambda function
    - severity: Filter by severity level
    - error_type: Filter by error type
    - limit: Maximum number of results (default: 100)
    """
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== ERROR QUERY HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            logger.info("✅ Handling CORS preflight request")
            processing_time = (datetime.now() - start_time).total_seconds()
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
                },
                "body": "",
                "processing_time": processing_time,
                "request_id": request_id
            }
        
        # Parse and validate query parameters
        logger.info("📊 Parsing query parameters...")
        query_params = event.get('queryStringParameters') or {}
        
        try:
            hours = int(query_params.get('hours', 24))
            if hours < 1 or hours > 168:  # Max 1 week
                raise ValueError("Hours must be between 1 and 168")
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid hours parameter: {e}")
            log_custom_error(
                'error-query-handler',
                f"Invalid hours parameter: {e}",
                {
                    'request_id': request_id,
                    'hours': query_params.get('hours'),
                    'error_type': 'ValidationError'
                },
                'WARNING'
            )
            hours = 24  # Default fallback
        
        try:
            limit = int(query_params.get('limit', 100))
            if limit < 1 or limit > 1000:  # Max 1000 results
                raise ValueError("Limit must be between 1 and 1000")
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid limit parameter: {e}")
            log_custom_error(
                'error-query-handler',
                f"Invalid limit parameter: {e}",
                {
                    'request_id': request_id,
                    'limit': query_params.get('limit'),
                    'error_type': 'ValidationError'
                },
                'WARNING'
            )
            limit = 100  # Default fallback
        
        source_lambda = query_params.get('source_lambda')
        severity = query_params.get('severity')
        error_type = query_params.get('error_type')
        
        # Validate severity if provided
        if severity and severity not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            logger.warning(f"⚠️ Invalid severity level: {severity}")
            log_custom_error(
                'error-query-handler',
                f"Invalid severity level: {severity}",
                {
                    'request_id': request_id,
                    'severity': severity,
                    'error_type': 'ValidationError'
                },
                'WARNING'
            )
            severity = None  # Ignore invalid severity
        
        logger.info(f"📊 Query params: hours={hours}, source={source_lambda}, severity={severity}, error_type={error_type}, limit={limit}")
        
        # Determine operation type
        path = event.get('path', '')
        logger.info(f"📊 Request path: {path}")
        
        if path == '/errors/summary':
            logger.info("📊 Processing error summary request")
            result = get_error_summary(hours, source_lambda, severity, error_type)
        elif path.startswith('/errors/'):
            # Extract error ID from path
            error_id = path.split('/')[-1]
            logger.info(f"📊 Processing error by ID request: {error_id}")
            result = get_error_by_id(error_id)
        else:
            logger.info("📊 Processing error list request")
            result = get_errors(hours, source_lambda, severity, error_type, limit)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 Total processing time: {processing_time:.3f}s")
        
        # Add processing time and request ID to result
        if isinstance(result, dict):
            result["processing_time"] = processing_time
            result["request_id"] = request_id
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result, default=str)
        }
        
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error in error query handler: {ve}")
        log_error(
            'error-query-handler',
            ve,
            context,
            {
                'request_id': request_id,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(ve),
                "error_type": "ValidationError",
                "request_id": request_id,
                "processing_time": processing_time
            })
        }
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error in error query handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'error-query-handler',
            e,
            context,
            {
                'request_id': request_id,
                'event_keys': list(event.keys()) if event else [],
                'processing_time': processing_time,
                'error_type': 'HandlerError'
            },
            'ERROR'
        )
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            })
        }

def get_error_summary(hours: int, source_lambda: str = None, 
                     severity: str = None, error_type: str = None) -> Dict[str, Any]:
    """Get error summary statistics with comprehensive logging and error handling"""
    try:
        logger.info(f"📊 Getting error summary for hours={hours}, source={source_lambda}, severity={severity}, error_type={error_type}")
        
        table = dynamodb.Table(ERROR_TABLE)
        
        # Calculate timestamp threshold
        threshold = int((datetime.now() - timedelta(hours=hours)).timestamp())
        logger.info(f"📊 Timestamp threshold: {threshold} ({datetime.fromtimestamp(threshold).isoformat()})")
        
        # Build filter expression
        filter_expression = "timestamp > :threshold"
        expression_values = {':threshold': threshold}
        
        if source_lambda:
            filter_expression += " AND source_lambda = :source"
            expression_values[':source'] = source_lambda
            logger.info(f"📊 Added source filter: {source_lambda}")
        
        if severity:
            filter_expression += " AND severity = :severity"
            expression_values[':severity'] = severity
            logger.info(f"📊 Added severity filter: {severity}")
        
        if error_type:
            filter_expression += " AND error_type = :error_type"
            expression_values[':error_type'] = error_type
            logger.info(f"📊 Added error_type filter: {error_type}")
        
        logger.info(f"📊 Filter expression: {filter_expression}")
        logger.info(f"📊 Expression values: {expression_values}")
        
        # Scan table
        logger.info("📊 Scanning DynamoDB table...")
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_values
        )
        
        errors = response.get('Items', [])
        logger.info(f"📊 Found {len(errors)} errors matching criteria")
        
        # Calculate statistics
        stats = {
            'total_errors': len(errors),
            'time_period_hours': hours,
            'by_source_lambda': {},
            'by_severity': {},
            'by_error_type': {},
            'by_hour': {},
            'recent_errors': errors[-10:] if errors else []
        }
        
        # Group by various dimensions
        logger.info("📊 Processing error statistics...")
        for error in errors:
            source = error.get('source_lambda', 'unknown')
            sev = error.get('severity', 'ERROR')
            err_type = error.get('error_type', 'UnknownError')
            timestamp = error.get('timestamp', '')
            
            # Group by source
            stats['by_source_lambda'][source] = stats['by_source_lambda'].get(source, 0) + 1
            
            # Group by severity
            stats['by_severity'][sev] = stats['by_severity'].get(sev, 0) + 1
            
            # Group by error type
            stats['by_error_type'][err_type] = stats['by_error_type'].get(err_type, 0) + 1
            
            # Group by hour
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:00')
                    stats['by_hour'][hour] = stats['by_hour'].get(hour, 0) + 1
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse timestamp {timestamp}: {e}")
                    pass
        
        # Sort by count
        stats['by_source_lambda'] = dict(sorted(stats['by_source_lambda'].items(), 
                                              key=lambda x: x[1], reverse=True))
        stats['by_severity'] = dict(sorted(stats['by_severity'].items(), 
                                         key=lambda x: x[1], reverse=True))
        stats['by_error_type'] = dict(sorted(stats['by_error_type'].items(), 
                                           key=lambda x: x[1], reverse=True))
        
        logger.info(f"📊 Summary statistics calculated: {len(stats['by_source_lambda'])} sources, {len(stats['by_severity'])} severities, {len(stats['by_error_type'])} error types")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get error summary: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {'error': str(e)}

def get_errors(hours: int, source_lambda: str = None, 
               severity: str = None, error_type: str = None, 
               limit: int = 100) -> Dict[str, Any]:
    """Get detailed error list with comprehensive logging and error handling"""
    try:
        logger.info(f"📊 Getting errors for hours={hours}, source={source_lambda}, severity={severity}, error_type={error_type}, limit={limit}")
        
        table = dynamodb.Table(ERROR_TABLE)
        
        # Calculate timestamp threshold
        threshold = int((datetime.now() - timedelta(hours=hours)).timestamp())
        logger.info(f"📊 Timestamp threshold: {threshold} ({datetime.fromtimestamp(threshold).isoformat()})")
        
        # Build filter expression
        filter_expression = "timestamp > :threshold"
        expression_values = {':threshold': threshold}
        
        if source_lambda:
            filter_expression += " AND source_lambda = :source"
            expression_values[':source'] = source_lambda
            logger.info(f"📊 Added source filter: {source_lambda}")
        
        if severity:
            filter_expression += " AND severity = :severity"
            expression_values[':severity'] = severity
            logger.info(f"📊 Added severity filter: {severity}")
        
        if error_type:
            filter_expression += " AND error_type = :error_type"
            expression_values[':error_type'] = error_type
            logger.info(f"📊 Added error_type filter: {error_type}")
        
        logger.info(f"📊 Filter expression: {filter_expression}")
        logger.info(f"📊 Expression values: {expression_values}")
        
        # Scan table
        logger.info(f"📊 Scanning DynamoDB table with limit {limit}...")
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_values,
            Limit=limit
        )
        
        errors = response.get('Items', [])
        logger.info(f"📊 Found {len(errors)} errors matching criteria")
        
        # Sort by timestamp (newest first)
        logger.info("📊 Sorting errors by timestamp...")
        errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        result = {
            'errors': errors,
            'total_count': len(errors),
            'time_period_hours': hours,
            'filters': {
                'source_lambda': source_lambda,
                'severity': severity,
                'error_type': error_type
            }
        }
        
        logger.info(f"📊 Returning {len(errors)} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get errors: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {'error': str(e)}

def get_error_by_id(error_id: str) -> Dict[str, Any]:
    """Get specific error by ID with comprehensive logging and error handling"""
    try:
        logger.info(f"📊 Getting error by ID: {error_id}")
        
        if not error_id or not isinstance(error_id, str):
            logger.error(f"❌ Invalid error ID: {error_id}")
            return {'error': 'Invalid error ID provided'}
        
        table = dynamodb.Table(ERROR_TABLE)
        
        logger.info(f"📊 Querying DynamoDB for error_id: {error_id}")
        response = table.get_item(Key={'error_id': error_id})
        
        if 'Item' in response:
            logger.info(f"✅ Found error: {error_id}")
            return {'error': response['Item']}
        else:
            logger.warning(f"⚠️ Error not found: {error_id}")
            return {'error': 'Error not found'}
            
    except Exception as e:
        logger.error(f"❌ Failed to get error by ID: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {'error': str(e)}
