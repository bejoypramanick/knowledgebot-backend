import json
import boto3
import logging
import traceback
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import os

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handler to ensure logs are captured
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Initialize AWS clients
s3_client = boto3.client('s3')
logger.info("✅ Initialized S3 client")

def generate_presigned_url(filename: str, content_type: str = None) -> Dict[str, Any]:
    """Generate presigned URL for S3 upload - BUSINESS LOGIC"""
    try:
        logger.info(f"🔗 Generating presigned URL for file: {filename}")
        
        # Generate unique document ID and S3 key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"doc_{timestamp}_{hash(filename) % 10000:04d}"
        s3_key = f"documents/{timestamp}/{document_id}/{filename}"
        
        # Get S3 bucket from environment
        bucket_name = os.environ.get('DOCUMENTS_BUCKET', 'knowledgebot-documents')
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type or 'application/octet-stream'
            },
            ExpiresIn=3600  # 1 hour
        )
        
        logger.info(f"✅ Generated presigned URL for: {filename}")
        logger.info(f"S3 Key: {s3_key}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "presigned_url": presigned_url,
                "document_id": document_id,
                "s3_key": s3_key,
                "bucket": bucket_name,
                "expires_in": 3600
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating presigned URL: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }

def list_files(bucket: str = None, prefix: str = "") -> Dict[str, Any]:
    """List files in S3 bucket - BUSINESS LOGIC"""
    try:
        bucket_name = bucket or os.environ.get('DOCUMENTS_BUCKET', 'knowledgebot-documents')
        logger.info(f"📁 Listing files in S3 bucket: {bucket_name}")
        
        # List objects in S3
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=1000
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag'].strip('"')
                })
        
        logger.info(f"✅ Listed {len(files)} files from S3")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "files": files,
                "count": len(files),
                "bucket": bucket_name,
                "prefix": prefix
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing files: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }

def download_file(bucket: str, key: str) -> Dict[str, Any]:
    """Download file from S3 - BUSINESS LOGIC"""
    try:
        logger.info(f"📥 Downloading file from S3: s3://{bucket}/{key}")
        
        # Get object from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Get content type
        content_type = response.get('ContentType', 'application/octet-stream')
        
        logger.info(f"✅ Successfully downloaded {len(content)} bytes from S3")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": content_type,
                "Content-Length": str(len(content))
            },
            "body": content,
            "isBase64Encoded": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error downloading file: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }

def upload_file(bucket: str, key: str, content: bytes, content_type: str = None) -> Dict[str, Any]:
    """Upload file to S3 - BUSINESS LOGIC"""
    try:
        logger.info(f"📤 Uploading file to S3: s3://{bucket}/{key}")
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type or 'application/octet-stream'
        )
        
        s3_path = f"s3://{bucket}/{key}"
        logger.info(f"✅ Successfully uploaded file to S3: {s3_path}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "s3_path": s3_path,
                "bucket": bucket,
                "key": key,
                "size": len(content)
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Error uploading file: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }

def delete_file(bucket: str, key: str) -> Dict[str, Any]:
    """Delete file from S3 - BUSINESS LOGIC"""
    try:
        logger.info(f"🗑️ Deleting file from S3: s3://{bucket}/{key}")
        
        # Delete from S3
        s3_client.delete_object(Bucket=bucket, Key=key)
        
        logger.info(f"✅ Successfully deleted file from S3: s3://{bucket}/{key}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": f"File {key} deleted successfully",
                "bucket": bucket,
                "key": key
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Error deleting file: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for S3 operations - BUSINESS LOGIC"""
    logger.info("=== S3 UNIFIED HANDLER STARTED ===")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Extract HTTP method and path
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        logger.info(f"🔍 HTTP Method: {http_method}, Path: {path}")
        logger.info(f"📊 Path parameters: {path_parameters}")
        logger.info(f"📊 Query parameters: {query_parameters}")
        
        # Route based on HTTP method and path
        if http_method == 'POST' and '/upload/presigned-url' in path:
            # Generate presigned URL
            body = json.loads(event.get('body', '{}'))
            filename = body.get('filename', 'document.pdf')
            content_type = body.get('content_type')
            return generate_presigned_url(filename, content_type)
            
        elif http_method == 'GET' and '/files' in path:
            # List files
            bucket = query_parameters.get('bucket')
            prefix = query_parameters.get('prefix', '')
            return list_files(bucket, prefix)
            
        elif http_method == 'GET' and '/files/' in path:
            # Download file
            file_key = path_parameters.get('key', '')
            bucket = query_parameters.get('bucket') or os.environ.get('DOCUMENTS_BUCKET', 'knowledgebot-documents')
            return download_file(bucket, file_key)
            
        elif http_method == 'POST' and '/upload' in path:
            # Upload file
            body = json.loads(event.get('body', '{}'))
            bucket = body.get('bucket') or os.environ.get('DOCUMENTS_BUCKET', 'knowledgebot-documents')
            key = body.get('key', '')
            content = body.get('content', '').encode()
            content_type = body.get('content_type')
            return upload_file(bucket, key, content, content_type)
            
        elif http_method == 'DELETE' and '/files/' in path:
            # Delete file
            file_key = path_parameters.get('key', '')
            bucket = query_parameters.get('bucket') or os.environ.get('DOCUMENTS_BUCKET', 'knowledgebot-documents')
            return delete_file(bucket, file_key)
            
        else:
            logger.warning(f"⚠️ Unsupported operation: {http_method} {path}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": f"Unsupported operation: {http_method} {path}"
                })
            }
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in S3 handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({
                "success": False,
                "error": f"Invalid JSON in request: {e}",
                "error_type": "JSONDecodeError",
                "timestamp": datetime.now().isoformat()
            })
        }
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in S3 handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Full stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            })
        }
