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
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Configuration
ERROR_TABLE = os.environ.get('ERROR_TABLE', 'knowledgebot-error-logs')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Error query handler for retrieving and analyzing error logs
    
    Query parameters:
    - hours: Number of hours to look back (default: 24)
    - source_lambda: Filter by source Lambda function
    - severity: Filter by severity level
    - error_type: Filter by error type
    - limit: Maximum number of results (default: 100)
    """
    try:
        logger.info("=== ERROR QUERY HANDLER STARTED ===")
        
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
                },
                "body": ""
            }
        
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        hours = int(query_params.get('hours', 24))
        source_lambda = query_params.get('source_lambda')
        severity = query_params.get('severity')
        error_type = query_params.get('error_type')
        limit = int(query_params.get('limit', 100))
        
        logger.info(f"📊 Query params: hours={hours}, source={source_lambda}, severity={severity}")
        
        # Get error summary
        if event.get('path') == '/errors/summary':
            result = get_error_summary(hours, source_lambda, severity, error_type)
        else:
            result = get_errors(hours, source_lambda, severity, error_type, limit)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result, default=str)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in error query handler: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e),
                "message": "Failed to query errors"
            })
        }

def get_error_summary(hours: int, source_lambda: str = None, 
                     severity: str = None, error_type: str = None) -> Dict[str, Any]:
    """Get error summary statistics"""
    try:
        table = dynamodb.Table(ERROR_TABLE)
        
        # Calculate timestamp threshold
        threshold = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        # Build filter expression
        filter_expression = "timestamp > :threshold"
        expression_values = {':threshold': threshold}
        
        if source_lambda:
            filter_expression += " AND source_lambda = :source"
            expression_values[':source'] = source_lambda
        
        if severity:
            filter_expression += " AND severity = :severity"
            expression_values[':severity'] = severity
        
        if error_type:
            filter_expression += " AND error_type = :error_type"
            expression_values[':error_type'] = error_type
        
        # Scan table
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_values
        )
        
        errors = response.get('Items', [])
        
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
                except:
                    pass
        
        # Sort by count
        stats['by_source_lambda'] = dict(sorted(stats['by_source_lambda'].items(), 
                                              key=lambda x: x[1], reverse=True))
        stats['by_severity'] = dict(sorted(stats['by_severity'].items(), 
                                         key=lambda x: x[1], reverse=True))
        stats['by_error_type'] = dict(sorted(stats['by_error_type'].items(), 
                                           key=lambda x: x[1], reverse=True))
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get error summary: {e}")
        return {'error': str(e)}

def get_errors(hours: int, source_lambda: str = None, 
               severity: str = None, error_type: str = None, 
               limit: int = 100) -> Dict[str, Any]:
    """Get detailed error list"""
    try:
        table = dynamodb.Table(ERROR_TABLE)
        
        # Calculate timestamp threshold
        threshold = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        # Build filter expression
        filter_expression = "timestamp > :threshold"
        expression_values = {':threshold': threshold}
        
        if source_lambda:
            filter_expression += " AND source_lambda = :source"
            expression_values[':source'] = source_lambda
        
        if severity:
            filter_expression += " AND severity = :severity"
            expression_values[':severity'] = severity
        
        if error_type:
            filter_expression += " AND error_type = :error_type"
            expression_values[':error_type'] = error_type
        
        # Scan table
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_values,
            Limit=limit
        )
        
        errors = response.get('Items', [])
        
        # Sort by timestamp (newest first)
        errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return {
            'errors': errors,
            'total_count': len(errors),
            'time_period_hours': hours,
            'filters': {
                'source_lambda': source_lambda,
                'severity': severity,
                'error_type': error_type
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get errors: {e}")
        return {'error': str(e)}

def get_error_by_id(error_id: str) -> Dict[str, Any]:
    """Get specific error by ID"""
    try:
        table = dynamodb.Table(ERROR_TABLE)
        
        response = table.get_item(Key={'error_id': error_id})
        
        if 'Item' in response:
            return {'error': response['Item']}
        else:
            return {'error': 'Error not found'}
            
    except Exception as e:
        logger.error(f"❌ Failed to get error by ID: {e}")
        return {'error': str(e)}
