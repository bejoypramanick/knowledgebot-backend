#!/usr/bin/env python3
"""
Script to populate the knowledge_base_metadata table with existing uploaded documents from S3.
This ensures all previously uploaded documents appear in the Knowledge Base Management screen.
"""

import boto3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Configuration
REGION = 'ap-south-1'
MAIN_BUCKET = 'chatbot-storage-ap-south-1'
METADATA_TABLE = 'chatbot-knowledge-base-metadata'

def get_s3_client():
    """Get S3 client"""
    return boto3.client('s3', region_name=REGION)

def get_dynamodb_resource():
    """Get DynamoDB resource"""
    return boto3.resource('dynamodb', region_name=REGION)

def list_existing_documents() -> List[Dict[str, Any]]:
    """List all existing documents in S3"""
    s3_client = get_s3_client()
    
    print("🔍 Scanning S3 for existing documents...")
    
    documents = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=MAIN_BUCKET, Prefix='documents/'):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if key.endswith(('.pdf', '.docx', '.txt', '.md', '.html')):
                    # Extract filename from S3 key
                    filename = key.split('/')[-1]
                    
                    # Get object metadata
                    try:
                        response = s3_client.head_object(Bucket=MAIN_BUCKET, Key=key)
                        content_type = response.get('ContentType', 'application/octet-stream')
                        file_size = response.get('ContentLength', 0)
                    except Exception as e:
                        print(f"⚠️  Could not get metadata for {key}: {e}")
                        content_type = 'application/octet-stream'
                        file_size = obj.get('Size', 0)
                    
                    documents.append({
                        's3_key': key,
                        'filename': filename,
                        'content_type': content_type,
                        'file_size': file_size,
                        'last_modified': obj['LastModified']
                    })
    
    print(f"📄 Found {len(documents)} existing documents")
    return documents

def create_document_metadata(s3_key: str, filename: str, content_type: str, 
                           file_size: int, last_modified: datetime) -> Dict[str, Any]:
    """Create document metadata entry"""
    
    # Generate a new document ID (we'll use the S3 key as base for consistency)
    # Extract the UUID from the S3 key if it exists, otherwise generate new one
    if 'documents/' in s3_key:
        key_part = s3_key.replace('documents/', '')
        file_extension = key_part.split('.')[-1] if '.' in key_part else ''
        base_name = key_part.replace(f'.{file_extension}', '') if file_extension else key_part
        
        # Try to use existing UUID if it looks like one, otherwise generate new
        try:
            # Check if it's already a UUID
            uuid.UUID(base_name)
            document_id = base_name
        except ValueError:
            # Not a UUID, generate new one
            document_id = str(uuid.uuid4())
    else:
        document_id = str(uuid.uuid4())
    
    # Generate download URL
    s3_client = get_s3_client()
    try:
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': MAIN_BUCKET,
                'Key': s3_key
            },
            ExpiresIn=86400 * 7  # 7 days
        )
    except Exception as e:
        print(f"⚠️  Could not generate download URL for {s3_key}: {e}")
        download_url = f"https://{MAIN_BUCKET}.s3.{REGION}.amazonaws.com/{s3_key}"
    
    return {
        'document_id': document_id,
        'original_filename': filename,
        's3_key': s3_key,
        's3_bucket': MAIN_BUCKET,
        's3_download_url': download_url,
        'content_type': content_type,
        'status': 'uploaded',  # Mark as uploaded since they exist in S3
        'uploaded_at': last_modified.isoformat(),
        'metadata': {
            'title': filename.replace('.' + filename.split('.')[-1], '') if '.' in filename else filename,
            'category': 'general',
            'tags': [],
            'author': 'unknown'
        },
        'file_size': file_size,
        'chunks_count': 0,  # Will be updated when RAG processing completes
        'processed_at': None
    }

def populate_metadata_table():
    """Populate the metadata table with existing documents"""
    
    print("🚀 Starting metadata table population...")
    
    # Get existing documents from S3
    documents = list_existing_documents()
    
    if not documents:
        print("ℹ️  No existing documents found in S3")
        return
    
    # Get DynamoDB table
    dynamodb = get_dynamodb_resource()
    metadata_table = dynamodb.Table(METADATA_TABLE)
    
    print(f"📊 Populating metadata table with {len(documents)} documents...")
    
    success_count = 0
    error_count = 0
    
    for doc in documents:
        try:
            # Create metadata entry
            metadata = create_document_metadata(
                s3_key=doc['s3_key'],
                filename=doc['filename'],
                content_type=doc['content_type'],
                file_size=doc['file_size'],
                last_modified=doc['last_modified']
            )
            
            # Store in DynamoDB
            metadata_table.put_item(Item=metadata)
            success_count += 1
            print(f"✅ Added: {doc['filename']} (ID: {metadata['document_id']})")
            
        except Exception as e:
            error_count += 1
            print(f"❌ Error adding {doc['filename']}: {e}")
    
    print(f"\n🎉 Population complete!")
    print(f"✅ Successfully added: {success_count} documents")
    print(f"❌ Errors: {error_count} documents")
    
    if success_count > 0:
        print(f"\n📋 You can now view these documents in the Knowledge Base Management screen!")

def main():
    """Main function"""
    try:
        populate_metadata_table()
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
