#!/usr/bin/env python3
"""
Presigned URL Generator - Single Purpose Lambda
Generates S3 presigned URLs for document uploads
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
import boto3
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Generate presigned URL for document upload"""
    logger.info("=== PRESIGNED URL GENERATOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        filename = body.get('filename', '')
        content_type = body.get('content_type', 'application/octet-stream')
        
        if not filename:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Filename is required"})
            }
        
        # Generate unique document ID and S3 key
        document_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"documents/{timestamp}/{document_id}/{filename}"
        
        # Get S3 bucket from environment
        bucket_name = os.environ.get('DOCUMENTS_BUCKET', 'chatbot-documents-ap-south-1')
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "presigned_url": presigned_url,
                "document_id": document_id,
                "s3_key": s3_key,
                "bucket": bucket_name,
                "expires_in": 3600
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
