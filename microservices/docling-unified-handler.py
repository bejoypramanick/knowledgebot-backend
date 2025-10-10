#!/usr/bin/env python3
"""
Docling Unified Handler - Complete Document Processing Pipeline
Handles document upload, processing, chunking, embedding generation, and storage
Direct S3 trigger without agent involvement
"""

import json
import os
import logging
import base64
import boto3
import uuid
import hashlib
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Initialize Docling components
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.document import DsDocument
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    
    # Initialize converter with optimized settings
    converter = DocumentConverter()
    logger.info("Docling initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Docling: {e}")
    converter = None

# Initialize sentence transformer for embeddings
try:
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Sentence transformer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize sentence transformer: {e}")
    embedding_model = None

def download_from_s3(bucket: str, key: str) -> bytes:
    """Download file from S3"""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Failed to download from S3: {e}")
        raise

def upload_to_s3(bucket: str, key: str, data: bytes) -> str:
    """Upload file to S3"""
    try:
        s3_client.put_object(Bucket=bucket, Key=key, Body=data)
        return f"s3://{bucket}/{key}"
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise

def process_document_with_docling(document_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process document using Docling with comprehensive extraction"""
    if not converter:
        raise Exception("Docling not available")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
        temp_path = temp_file.name
        temp_file.write(document_bytes)
    
    try:
        logger.info(f"Processing document: {filename}")
        
        # Convert document with Docling
        doc = converter.convert(temp_path)
        
        # Extract comprehensive information
        result = {
            "success": True,
            "document_type": doc.document_type,
            "metadata": {
                "title": getattr(doc, 'title', None),
                "author": getattr(doc, 'author', None),
                "creation_date": getattr(doc, 'creation_date', None),
                "modification_date": getattr(doc, 'modification_date', None),
                "page_count": len(doc.pages) if hasattr(doc, 'pages') else None
            },
            "content": {
                "text": doc.export_to_markdown(),
                "plain_text": doc.export_to_text(),
                "html": doc.export_to_html() if hasattr(doc, 'export_to_html') else None
            },
            "structure": [],
            "tables": [],
            "images": [],
            "chunks": []
        }
        
        # Extract structured elements and create hierarchical chunks
        for element in doc.iterate_items():
            element_data = {
                "text": element.text,
                "type": element.label,
                "page": getattr(element, 'page', None),
                "bbox": getattr(element, 'bbox', None),
                "confidence": getattr(element, 'confidence', None)
            }
            
            # Categorize elements
            if element.label in ['table', 'Table']:
                result["tables"].append(element_data)
            elif element.label in ['figure', 'image', 'Image']:
                result["images"].append(element_data)
            else:
                result["structure"].append(element_data)
            
            # Create chunks for RAG
            if element.text and len(element.text.strip()) > 10:
                chunk = {
                    "id": hashlib.md5(element.text.encode()).hexdigest(),
                    "text": element.text.strip(),
                    "type": element.label,
                    "page": getattr(element, 'page', None),
                    "metadata": {
                        "bbox": getattr(element, 'bbox', None),
                        "confidence": getattr(element, 'confidence', None)
                    }
                }
                result["chunks"].append(chunk)
        
        # Add summary statistics
        result["statistics"] = {
            "total_chunks": len(result["chunks"]),
            "total_tables": len(result["tables"]),
            "total_images": len(result["images"]),
            "total_structure_elements": len(result["structure"]),
            "document_size_bytes": len(document_bytes),
            "processing_timestamp": str(doc.creation_time) if hasattr(doc, 'creation_time') else None
        }
        
        logger.info(f"Document processed successfully: {result['statistics']['total_chunks']} chunks extracted")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate embeddings for document chunks using sentence transformer"""
    if not embedding_model:
        logger.warning("Embedding model not available, skipping embeddings")
        return chunks
    
    try:
        # Extract texts for embedding
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        embeddings = embedding_model.encode(texts)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i].tolist()
        
        logger.info(f"Generated embeddings for {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return chunks

def store_chunks_to_dynamodb(chunks: List[Dict[str, Any]], document_id: str, filename: str) -> bool:
    """Store document chunks to DynamoDB"""
    try:
        table_name = os.environ.get('CHUNKS_TABLE', 'document-chunks')
        table = dynamodb.Table(table_name)
        
        # Store each chunk
        for chunk in chunks:
            item = {
                'chunk_id': chunk['id'],
                'document_id': document_id,
                'filename': filename,
                'text': chunk['text'],
                'type': chunk['type'],
                'page': chunk.get('page'),
                'metadata': chunk.get('metadata', {}),
                'created_at': datetime.now().isoformat(),
                'ttl': int(time.time()) + (365 * 24 * 60 * 60)  # 1 year TTL
            }
            
            table.put_item(Item=item)
        
        logger.info(f"Stored {len(chunks)} chunks to DynamoDB")
        return True
        
    except Exception as e:
        logger.error(f"Error storing chunks to DynamoDB: {e}")
        return False

def store_embeddings_to_pinecone(chunks: List[Dict[str, Any]], document_id: str, namespace: str = None) -> bool:
    """Store embeddings to Pinecone using Lambda function"""
    try:
        # Prepare chunks with embeddings
        chunks_with_embeddings = []
        for chunk in chunks:
            if 'embedding' in chunk:
                chunks_with_embeddings.append({
                    'id': chunk['id'],
                    'values': chunk['embedding'],
                    'metadata': {
                        'document_id': document_id,
                        'text': chunk['text'],
                        'type': chunk['type'],
                        'page': chunk.get('page')
                    }
                })
        
        if not chunks_with_embeddings:
            logger.warning("No embeddings to store")
            return True
        
        # Call Pinecone upsert Lambda
        pinecone_function_name = os.environ.get('PINECONE_UPSERT_FUNCTION', 'pinecone-upsert-handler')
        
        payload = {
            'vectors': chunks_with_embeddings,
            'namespace': namespace or 'default'
        }
        
        response = lambda_client.invoke(
            FunctionName=pinecone_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            logger.info(f"Stored {len(chunks_with_embeddings)} embeddings to Pinecone")
            return True
        else:
            logger.error(f"Failed to store embeddings to Pinecone: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Error storing embeddings to Pinecone: {e}")
        return False

def store_relations_to_neo4j(chunks: List[Dict[str, Any]], document_id: str, filename: str) -> bool:
    """Store document relations to Neo4j using Lambda function"""
    try:
        # Prepare relations data
        relations_data = {
            'document_id': document_id,
            'filename': filename,
            'chunks': chunks,
            'metadata': {
                'total_chunks': len(chunks),
                'processing_timestamp': datetime.now().isoformat()
            }
        }
        
        # Call Neo4j write Lambda
        neo4j_function_name = os.environ.get('NEO4J_WRITE_FUNCTION', 'neo4j-write-handler')
        
        response = lambda_client.invoke(
            FunctionName=neo4j_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(relations_data)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            logger.info(f"Stored relations for document {document_id} to Neo4j")
            return True
        else:
            logger.error(f"Failed to store relations to Neo4j: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Error storing relations to Neo4j: {e}")
        return False

def store_markdown_to_s3(markdown_content: str, document_id: str, filename: str) -> str:
    """Store extracted markdown to S3"""
    try:
        bucket_name = os.environ.get('PROCESSED_DOCUMENTS_BUCKET', 'processed-documents')
        timestamp = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"processed/{timestamp}/{document_id}/{Path(filename).stem}.md"
        
        # Upload markdown content
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=markdown_content.encode('utf-8'),
            ContentType='text/markdown'
        )
        
        logger.info(f"Stored markdown to S3: s3://{bucket_name}/{s3_key}")
        return f"s3://{bucket_name}/{s3_key}"
        
    except Exception as e:
        logger.error(f"Error storing markdown to S3: {e}")
        raise

def process_document_pipeline(document_bytes: bytes, filename: str, document_id: str = None) -> Dict[str, Any]:
    """Complete document processing pipeline"""
    start_time = time.time()
    
    try:
        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())
        
        logger.info(f"Starting document processing pipeline for: {filename}")
        
        # Step 1: Process document with Docling
        logger.info("Step 1: Processing document with Docling")
        docling_result = process_document_with_docling(document_bytes, filename)
        
        if not docling_result["success"]:
            raise Exception("Document processing failed")
        
        # Step 2: Store markdown to S3
        logger.info("Step 2: Storing markdown to S3")
        markdown_s3_path = store_markdown_to_s3(
            docling_result["content"]["text"],
            document_id,
            filename
        )
        
        # Step 3: Generate embeddings for chunks
        logger.info("Step 3: Generating embeddings")
        chunks_with_embeddings = generate_embeddings(docling_result["chunks"])
        
        # Step 4: Store chunks to DynamoDB
        logger.info("Step 4: Storing chunks to DynamoDB")
        dynamodb_success = store_chunks_to_dynamodb(chunks_with_embeddings, document_id, filename)
        
        # Step 5: Store embeddings to Pinecone
        logger.info("Step 5: Storing embeddings to Pinecone")
        pinecone_success = store_embeddings_to_pinecone(chunks_with_embeddings, document_id)
        
        # Step 6: Store relations to Neo4j
        logger.info("Step 6: Storing relations to Neo4j")
        neo4j_success = store_relations_to_neo4j(chunks_with_embeddings, document_id, filename)
        
        processing_time = time.time() - start_time
        
        result = {
            "success": True,
            "document_id": document_id,
            "filename": filename,
            "processing_time": processing_time,
            "markdown_s3_path": markdown_s3_path,
            "statistics": docling_result["statistics"],
            "storage_results": {
                "dynamodb": dynamodb_success,
                "pinecone": pinecone_success,
                "neo4j": neo4j_success
            },
            "chunks_processed": len(chunks_with_embeddings),
            "embeddings_generated": len([c for c in chunks_with_embeddings if 'embedding' in c])
        }
        
        logger.info(f"Document processing pipeline completed successfully in {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Document processing pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
            "filename": filename,
            "processing_time": time.time() - start_time
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for S3-triggered document processing"""
    logger.info("=== DOCLING UNIFIED PROCESSOR STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Handle S3 event
        records = event.get('Records', [])
        if not records:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "No S3 records found in event"
                })
            }
        
        record = records[0]
        s3_info = record.get('s3', {})
        bucket = s3_info.get('bucket', {}).get('name', '')
        key = s3_info.get('object', {}).get('key', '')
        
        if not bucket or not key:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid S3 event data"
                })
            }
        
        logger.info(f"Processing document from S3: s3://{bucket}/{key}")
        
        # Download document from S3
        document_bytes = download_from_s3(bucket, key)
        filename = Path(key).name
        
        # Extract document ID from S3 key or metadata
        document_id = None
        try:
            # Try to get document ID from S3 object metadata
            response = s3_client.head_object(Bucket=bucket, Key=key)
            metadata = response.get('Metadata', {})
            document_id = metadata.get('document_id')
        except:
            pass
        
        # If no document ID in metadata, extract from S3 key path
        if not document_id:
            path_parts = key.split('/')
            if len(path_parts) >= 3 and path_parts[0] == 'documents':
                document_id = path_parts[2]  # documents/YYYY/MM/DD/{document_id}/filename
        
        # Process document through complete pipeline
        result = process_document_pipeline(document_bytes, filename, document_id)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
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
                "error": str(e),
                "error_type": type(e).__name__
            })
        }
