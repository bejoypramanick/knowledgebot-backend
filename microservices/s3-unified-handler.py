#!/usr/bin/env python3
"""
S3 Unified Handler - Single Purpose Lambda
Handles both S3 presigned URL generation and S3 data reading
"""

import json
import os
import boto3
from typing import Dict, Any
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize S3 client
try:
    s3_client = boto3.client('s3')
    logger.info("S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    s3_client = None

def generate_presigned_url(bucket: str, key: str, operation: str = 'put_object', expiration: int = 3600) -> Dict[str, Any]:
    """Generate presigned URL for S3 operations"""
    try:
        if not s3_client:
            return {
                "success": False,
                "error": "S3 client not available"
            }
        
        # Generate presigned URL
        if operation == 'put_object':
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
        elif operation == 'get_object':
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
        else:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}"
            }
        
        return {
            "success": True,
            "presigned_url": presigned_url,
            "bucket": bucket,
            "key": key,
            "operation": operation,
            "expiration": expiration
        }
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def read_s3_data(bucket: str, key: str) -> Dict[str, Any]:
    """Read data from S3"""
    try:
        if not s3_client:
            return {
                "success": False,
                "error": "S3 client not available"
            }
        
        # Get object from S3
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
            "success": True,
            "content": content_str,
            "content_type": content_type,
            "bucket": bucket,
            "key": key,
            "size": len(content),
            "metadata": response.get('Metadata', {})
        }
    except ClientError as e:
        logger.error(f"Error reading S3 data: {e}")
        return {
            "success": False,
            "error": str(e),
            "bucket": bucket,
            "key": key
        }

def list_s3_objects(bucket: str, prefix: str = '', max_keys: int = 1000) -> Dict[str, Any]:
    """List objects in S3 bucket"""
    try:
        if not s3_client:
            return {
                "success": False,
                "error": "S3 client not available"
            }
        
        # List objects
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                objects.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag']
                })
        
        return {
            "success": True,
            "objects": objects,
            "bucket": bucket,
            "prefix": prefix,
            "total_count": len(objects),
            "is_truncated": response.get('IsTruncated', False)
        }
    except ClientError as e:
        logger.error(f"Error listing S3 objects: {e}")
        return {
            "success": False,
            "error": str(e),
            "bucket": bucket,
            "prefix": prefix
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Unified S3 handler for presigned URLs, reading, and listing"""
    logger.info("=== S3 UNIFIED HANDLER STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract operation type
        operation_type = body.get('operation_type', 'presigned_url')  # 'presigned_url', 'read', 'list'
        
        if operation_type == 'presigned_url':
            # Generate presigned URL
            bucket = body.get('bucket', '')
            key = body.get('key', '')
            operation = body.get('operation', 'put_object')
            expiration = body.get('expiration', 3600)
            
            if not bucket or not key:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Bucket and key are required for presigned URL"})
                }
            
            result = generate_presigned_url(bucket, key, operation, expiration)
            
        elif operation_type == 'read':
            # Read S3 data
            bucket = body.get('bucket', '')
            key = body.get('key', '')
            
            if not bucket or not key:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Bucket and key are required for read operation"})
                }
            
            result = read_s3_data(bucket, key)
            
        elif operation_type == 'list':
            # List S3 objects
            bucket = body.get('bucket', '')
            prefix = body.get('prefix', '')
            max_keys = body.get('max_keys', 1000)
            
            if not bucket:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Bucket is required for list operation"})
                }
            
            result = list_s3_objects(bucket, prefix, max_keys)
            
        else:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Operation type must be 'presigned_url', 'read', or 'list'"})
            }
        
        return {
            "statusCode": 200 if result["success"] else 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in S3 unified handler: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
