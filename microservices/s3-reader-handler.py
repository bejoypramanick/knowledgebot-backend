#!/usr/bin/env python3
"""
S3 Reader - Single Purpose Lambda
Reads data from S3 buckets
"""

import json
import os
from typing import Dict, Any
import boto3
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Read data from S3 bucket"""
    logger.info("=== S3 READER STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        bucket = body.get('bucket', '')
        key = body.get('key', '')
        
        if not bucket or not key:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Bucket and key are required"})
            }
        
        # Read from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Try to decode as text, fallback to base64
        try:
            content_str = content.decode('utf-8')
            content_type = 'text'
        except UnicodeDecodeError:
            import base64
            content_str = base64.b64encode(content).decode('utf-8')
            content_type = 'binary'
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "content": content_str,
                "content_type": content_type,
                "size": len(content),
                "bucket": bucket,
                "key": key
            })
        }
        
    except Exception as e:
        logger.error(f"Error reading from S3: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
