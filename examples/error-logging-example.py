#!/usr/bin/env python3
"""
Example: How to use the centralized error logger in your Lambda functions

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

import json
import logging
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_timeout_error, log_service_failure

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """Example Lambda function with error logging"""
    try:
        logger.info("=== EXAMPLE LAMBDA STARTED ===")
        
        # Your business logic here
        result = process_request(event)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "result": result
            })
        }
        
    except TimeoutError as e:
        logger.error(f"⏰ Timeout error: {e}")
        
        # Log timeout error
        error_id = log_timeout_error(
            'example-lambda',
            'request_processing',
            context,
            {'event': event}
        )
        
        return {
            "statusCode": 408,
            "body": json.dumps({
                "success": False,
                "error": "Request timeout",
                "error_id": error_id
            })
        }
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {e}")
        
        # Log validation error
        error_id = log_error(
            'example-lambda',
            e,
            context,
            {'event': event, 'user_id': event.get('user_id')},
            'ERROR'
        )
        
        return {
            "statusCode": 400,
            "body": json.dumps({
                "success": False,
                "error": "Invalid request",
                "error_id": error_id
            })
        }
        
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        
        # Log unexpected error
        error_id = log_error(
            'example-lambda',
            e,
            context,
            {'event': event},
            'CRITICAL'
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": "Internal server error",
                "error_id": error_id
            })
        }

def process_request(event):
    """Example business logic"""
    # Simulate some processing
    if 'test_error' in event:
        raise ValueError("Test error for demonstration")
    
    if 'test_timeout' in event:
        raise TimeoutError("Test timeout for demonstration")
    
    return {"message": "Processing completed successfully"}

# Example of logging service failures
def call_external_service():
    """Example of logging service failures"""
    try:
        # Simulate external service call
        # response = requests.get('https://api.example.com/data')
        # return response.json()
        pass
    except Exception as e:
        # Log service failure
        error_id = log_service_failure(
            'example-lambda',
            'external-api',
            str(e),
            None,
            {'service_url': 'https://api.example.com/data'}
        )
        raise

# Example of logging custom errors
def validate_user_input(data):
    """Example of logging custom validation errors"""
    if not data.get('email'):
        error_id = log_custom_error(
            'example-lambda',
            'ValidationError',
            'Email is required',
            None,
            {'user_id': data.get('user_id')},
            'WARNING'
        )
        raise ValueError("Email is required")
    
    return True
