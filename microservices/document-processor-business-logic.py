#!/usr/bin/env python3
"""
Document Processor Business Logic - Zip Lambda
ALL business logic and CRUD operations for document processing
Uses library Lambdas for heavy operations
"""

import json
import os
import logging
import base64
import boto3
import uuid
import hashlib
import time
import traceback
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_timeout_error, log_service_failure

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
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

def download_from_s3(bucket: str, key: str) -> bytes:
    """Download file from S3 with comprehensive error handling and logging"""
    start_time = datetime.now()
    
    try:
        logger.info(f"📥 Starting S3 download: s3://{bucket}/{key}")
        logger.info(f"📊 Bucket: {bucket}")
        logger.info(f"📊 Key: {key}")
        
        # Validate input parameters
        if not bucket or not isinstance(bucket, str):
            raise ValueError("Bucket name must be a non-empty string")
        if not key or not isinstance(key, str):
            raise ValueError("S3 key must be a non-empty string")
        
        # Check if object exists first (optimization)
        try:
            head_response = s3_client.head_object(Bucket=bucket, Key=key)
            content_length = head_response.get('ContentLength', 0)
            content_type = head_response.get('ContentType', 'unknown')
            last_modified = head_response.get('LastModified')
            
            logger.info(f"📊 Object exists - Size: {content_length} bytes, Type: {content_type}")
            logger.info(f"📊 Last modified: {last_modified}")
            
            # Check file size limits (prevent memory issues)
            MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
            if content_length > MAX_FILE_SIZE:
                raise ValueError(f"File too large: {content_length} bytes (max: {MAX_FILE_SIZE})")
                
        except s3_client.exceptions.NoSuchKey:
            logger.error(f"❌ S3 object not found: s3://{bucket}/{key}")
            raise Exception(f"S3 object not found: s3://{bucket}/{key}")
        except s3_client.exceptions.NoSuchBucket:
            logger.error(f"❌ S3 bucket not found: {bucket}")
            raise Exception(f"S3 bucket not found: {bucket}")
        
        # Download the object
        response = s3_client.get_object(Bucket=bucket, Key=key)
        logger.info(f"📊 S3 response status: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
        
        # Read content in chunks for large files (memory optimization)
        document_bytes = b''
        content_stream = response['Body']
        
        # Read in 1MB chunks
        chunk_size = 1024 * 1024
        while True:
            chunk = content_stream.read(chunk_size)
            if not chunk:
                break
            document_bytes += chunk
            
            # Log progress for large files
            if len(document_bytes) % (10 * chunk_size) == 0:  # Every 10MB
                logger.info(f"📊 Downloaded {len(document_bytes)} bytes so far...")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Successfully downloaded {len(document_bytes)} bytes from S3")
        logger.info(f"📊 Download time: {processing_time:.3f}s")
        logger.info(f"📊 Download speed: {len(document_bytes) / processing_time / 1024 / 1024:.2f} MB/s")
        
        # Log success to centralized error logger
        log_custom_error(
            'document-processor-business-logic',
            's3_download_success',
            {
                'bucket': bucket,
                'key': key,
                'file_size': len(document_bytes),
                'processing_time': processing_time,
                'download_speed_mbps': len(document_bytes) / processing_time / 1024 / 1024
            },
            'INFO'
        )
        
        return document_bytes
        
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error downloading from S3: {ve}")
        log_error(
            'document-processor-business-logic',
            ve,
            None,
            {
                'bucket': bucket,
                'key': key,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        raise
    except s3_client.exceptions.NoSuchKey as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ S3 object not found: s3://{bucket}/{key}")
        logger.error(f"📊 Error details: {e}")
        log_error(
            'document-processor-business-logic',
            e,
            None,
            {
                'bucket': bucket,
                'key': key,
                'processing_time': processing_time,
                'error_type': 'NoSuchKey'
            },
            'ERROR'
        )
        raise Exception(f"S3 object not found: s3://{bucket}/{key}")
    except s3_client.exceptions.NoSuchBucket as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ S3 bucket not found: {bucket}")
        logger.error(f"📊 Error details: {e}")
        log_error(
            'document-processor-business-logic',
            e,
            None,
            {
                'bucket': bucket,
                'key': key,
                'processing_time': processing_time,
                'error_type': 'NoSuchBucket'
            },
            'ERROR'
        )
        raise Exception(f"S3 bucket not found: {bucket}")
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Failed to download from S3: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'document-processor-business-logic',
            e,
            None,
            {
                'bucket': bucket,
                'key': key,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        raise

def upload_to_s3(bucket: str, key: str, data: bytes) -> str:
    """Upload file to S3"""
    try:
        logger.info(f"📤 Uploading to S3: s3://{bucket}/{key}")
        s3_client.put_object(Bucket=bucket, Key=key, Body=data)
        s3_path = f"s3://{bucket}/{key}"
        logger.info(f"✅ Successfully uploaded to S3: {s3_path}")
        return s3_path
    except Exception as e:
        logger.error(f"❌ Failed to upload to S3: {e}")
        raise

def call_docling_library(document_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Call Docling library Lambda for document processing"""
    try:
        logger.info(f"🔧 Calling Docling library for document: {filename}")
        
        # Encode document bytes to base64 for Lambda payload
        document_b64 = base64.b64encode(document_bytes).decode('utf-8')
        
        payload = {
            'document_bytes': document_b64,
            'filename': filename
        }
        
        # Get Docling library function name from environment
        docling_function_name = os.environ.get('DOCLING_LIBRARY_FUNCTION', 'docling-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=docling_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            docling_result = json.loads(result['body'])
            if docling_result.get('success'):
                logger.info(f"✅ Docling library processed successfully: {docling_result['statistics']['total_chunks']} chunks")
                return docling_result
            else:
                logger.error(f"❌ Docling library processing failed: {docling_result.get('error')}")
                raise Exception(f"Docling processing failed: {docling_result.get('error')}")
        else:
            logger.error(f"❌ Docling library Lambda call failed: {result}")
            raise Exception(f"Docling Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Docling library: {e}")
        raise

def call_pinecone_for_embeddings(texts: List[str]) -> List[List[float]]:
    """Call Pinecone MCP server for embedding generation using native models with comprehensive logging"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🔧 Starting Pinecone MCP server call for {len(texts)} texts using native embedding models")
        logger.info(f"📊 Text lengths: {[len(text) for text in texts[:5]]}...")  # Log first 5 text lengths
        
        # Validate input parameters
        if not texts or not isinstance(texts, list):
            raise ValueError("Texts must be a non-empty list")
        
        if len(texts) == 0:
            raise ValueError("Texts list cannot be empty")
        
        # Check for empty or invalid texts
        valid_texts = []
        for i, text in enumerate(texts):
            if not text or not isinstance(text, str) or text.strip() == "":
                logger.warning(f"⚠️ Skipping invalid text at index {i}: {repr(text)}")
                continue
            if len(text) > 10000:  # Limit text length
                logger.warning(f"⚠️ Truncating long text at index {i} (length: {len(text)})")
                text = text[:10000]
            valid_texts.append(text.strip())
        
        if not valid_texts:
            raise ValueError("No valid texts found after validation")
        
        logger.info(f"📊 Valid texts after filtering: {len(valid_texts)}")
        
        payload = {
            'texts': valid_texts,
            'operation_type': 'generate_embeddings'
        }
        
        # Get Pinecone library function name from environment
        pinecone_function_name = os.environ.get('PINECONE_LIBRARY_FUNCTION', 'pinecone-library-handler')
        logger.info(f"📊 Calling Lambda function: {pinecone_function_name}")
        
        # Invoke Lambda with timeout handling
        response = lambda_client.invoke(
            FunctionName=pinecone_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Check Lambda invocation response
        status_code = response.get('StatusCode', 0)
        if status_code != 200:
            logger.error(f"❌ Lambda invocation failed with status: {status_code}")
            raise Exception(f"Lambda invocation failed with status: {status_code}")
        
        # Parse response
        response_payload = response['Payload'].read()
        if not response_payload:
            raise Exception("Empty response from Pinecone Lambda")
        
        result = json.loads(response_payload)
        logger.info(f"📊 Lambda response status: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            pinecone_result = json.loads(result['body'])
            logger.info(f"📊 Pinecone result keys: {list(pinecone_result.keys())}")
            
            if pinecone_result.get('success'):
                # Extract embeddings from Pinecone MCP server response
                embeddings = []
                embedding_data_list = pinecone_result.get('embeddings', [])
                
                logger.info(f"📊 Processing {len(embedding_data_list)} embedding results")
                
                for i, embedding_data in enumerate(embedding_data_list):
                    if embedding_data.get('embedding') is not None:
                        embedding = embedding_data['embedding']
                        if isinstance(embedding, list) and len(embedding) > 0:
                            embeddings.append(embedding)
                            logger.debug(f"📊 Added embedding {i+1}: {len(embedding)} dimensions")
                        else:
                            logger.warning(f"⚠️ Invalid embedding at index {i}: {type(embedding)}")
                            embeddings.append(None)
                    else:
                        logger.warning(f"⚠️ No embedding data at index {i}")
                        embeddings.append(None)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                valid_embeddings = [e for e in embeddings if e is not None]
                
                logger.info(f"✅ Pinecone MCP server generated {len(valid_embeddings)} valid embeddings using native models")
                logger.info(f"📊 Processing time: {processing_time:.3f}s")
                logger.info(f"📊 Embedding rate: {len(valid_embeddings) / processing_time:.2f} embeddings/sec")
                
                # Log success to centralized error logger
                log_custom_error(
                    'document-processor-business-logic',
                    'pinecone_embeddings_success',
                    {
                        'texts_count': len(valid_texts),
                        'embeddings_generated': len(valid_embeddings),
                        'processing_time': processing_time,
                        'embedding_rate': len(valid_embeddings) / processing_time,
                        'model': pinecone_result.get('method', 'unknown')
                    },
                    'INFO'
                )
                
                return embeddings
            else:
                error_msg = pinecone_result.get('error', 'Unknown error')
                logger.error(f"❌ Pinecone MCP server failed: {error_msg}")
                log_error(
                    'document-processor-business-logic',
                    Exception(error_msg),
                    None,
                    {
                        'texts_count': len(valid_texts),
                        'processing_time': (datetime.now() - start_time).total_seconds(),
                        'error_type': 'PineconeMCPError'
                    },
                    'ERROR'
                )
                raise Exception(f"Pinecone embedding generation failed: {error_msg}")
        else:
            error_msg = result.get('body', 'Unknown Lambda error')
            logger.error(f"❌ Pinecone MCP server Lambda call failed: {result}")
            log_error(
                'document-processor-business-logic',
                Exception(error_msg),
                None,
                {
                    'texts_count': len(valid_texts),
                    'processing_time': (datetime.now() - start_time).total_seconds(),
                    'error_type': 'LambdaInvocationError'
                },
                'ERROR'
            )
            raise Exception(f"Pinecone MCP server Lambda call failed: {result}")
            
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error calling Pinecone MCP server: {ve}")
        log_error(
            'document-processor-business-logic',
            ve,
            None,
            {
                'texts_count': len(texts) if texts else 0,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        raise
    except json.JSONDecodeError as je:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ JSON decode error calling Pinecone MCP server: {je}")
        log_error(
            'document-processor-business-logic',
            je,
            None,
            {
                'texts_count': len(texts) if texts else 0,
                'processing_time': processing_time,
                'error_type': 'JSONDecodeError'
            },
            'ERROR'
        )
        raise
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error calling Pinecone MCP server for embeddings: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'document-processor-business-logic',
            e,
            None,
            {
                'texts_count': len(texts) if texts else 0,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        raise

def call_pinecone_library(vectors: List[Dict[str, Any]], operation: str = 'upsert', namespace: str = None) -> Dict[str, Any]:
    """Call Pinecone library Lambda"""
    try:
        logger.info(f"🔧 Calling Pinecone library for {operation} operation with {len(vectors)} vectors")
        
        payload = {
            'operation_type': operation,
            'vectors': vectors,
            'namespace': namespace or 'default'
        }
        
        if operation == 'search':
            payload.update({
                'query_vector': vectors[0] if vectors else [],
                'limit': 10
            })
        
        # Get Pinecone library function name from environment
        pinecone_function_name = os.environ.get('PINECONE_LIBRARY_FUNCTION', 'pinecone-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=pinecone_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            pinecone_result = json.loads(result['body'])
            if pinecone_result.get('success'):
                logger.info(f"✅ Pinecone library {operation} completed successfully")
                return pinecone_result
            else:
                logger.error(f"❌ Pinecone library {operation} failed: {pinecone_result.get('error')}")
                raise Exception(f"Pinecone {operation} failed: {pinecone_result.get('error')}")
        else:
            logger.error(f"❌ Pinecone library Lambda call failed: {result}")
            raise Exception(f"Pinecone Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Pinecone library: {e}")
        raise

def call_neo4j_library(cypher_query: str, parameters: Dict[str, Any] = None, operation_type: str = "write") -> Dict[str, Any]:
    """Call Neo4j library Lambda"""
    try:
        logger.info(f"🔧 Calling Neo4j library for {operation_type} operation")
        
        payload = {
            'cypher_query': cypher_query,
            'parameters': parameters or {},
            'operation_type': operation_type
        }
        
        # Get Neo4j library function name from environment
        neo4j_function_name = os.environ.get('NEO4J_LIBRARY_FUNCTION', 'neo4j-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=neo4j_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            neo4j_result = json.loads(result['body'])
            if neo4j_result.get('success'):
                logger.info(f"✅ Neo4j library {operation_type} completed successfully")
                return neo4j_result
            else:
                logger.error(f"❌ Neo4j library {operation_type} failed: {neo4j_result.get('error')}")
                raise Exception(f"Neo4j {operation_type} failed: {neo4j_result.get('error')}")
        else:
            logger.error(f"❌ Neo4j library Lambda call failed: {result}")
            raise Exception(f"Neo4j Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Neo4j library: {e}")
        raise

def store_chunks_to_dynamodb(chunks: List[Dict[str, Any]], document_id: str, filename: str) -> bool:
    """Store document chunks to DynamoDB using MCP server - BUSINESS LOGIC"""
    try:
        logger.info(f"💾 Storing {len(chunks)} chunks to DynamoDB for document: {document_id}")
        
        table_name = os.environ.get('CHUNKS_TABLE', 'document-chunks')
        dynamodb_function_name = os.environ.get('DYNAMODB_MCP_FUNCTION', 'dynamodb-mcp-handler')
        
        # Store each chunk using DynamoDB MCP server
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
            
            payload = {
                'operation': 'write',
                'table_name': table_name,
                'item': item
            }
            
            response = lambda_client.invoke(
                FunctionName=dynamodb_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') != 200:
                logger.error(f"❌ Failed to store chunk {chunk['id']}: {result}")
                return False
        
        logger.info(f"✅ Successfully stored {len(chunks)} chunks to DynamoDB via MCP server")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error storing chunks to DynamoDB via MCP server: {e}")
        return False

def store_markdown_to_s3(markdown_content: str, document_id: str, filename: str) -> str:
    """Store extracted markdown to S3 - BUSINESS LOGIC"""
    try:
        logger.info(f"💾 Storing markdown to S3 for document: {document_id}")
        
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
        
        s3_path = f"s3://{bucket_name}/{s3_key}"
        logger.info(f"✅ Successfully stored markdown to S3: {s3_path}")
        return s3_path
        
    except Exception as e:
        logger.error(f"❌ Error storing markdown to S3: {e}")
        raise

def process_document_pipeline(document_bytes: bytes, filename: str, document_id: str = None) -> Dict[str, Any]:
    """Complete document processing pipeline - BUSINESS LOGIC ORCHESTRATION"""
    start_time = time.time()
    
    try:
        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())
        
        logger.info(f"🚀 Starting document processing pipeline for: {filename} (ID: {document_id})")
        
        # Step 1: Process document with Docling library
        logger.info("📄 Step 1: Processing document with Docling library")
        docling_result = call_docling_library(document_bytes, filename)
        
        if not docling_result["success"]:
            raise Exception("Document processing failed")
        
        # Step 2: Store markdown to S3
        logger.info("📝 Step 2: Storing markdown to S3")
        markdown_s3_path = store_markdown_to_s3(
            docling_result["content"]["text"],
            document_id,
            filename
        )
        
        # Step 3: Generate embeddings using Pinecone MCP server with native models
        logger.info("🧠 Step 3: Generating embeddings with Pinecone MCP server using native models")
        texts = [chunk["text"] for chunk in docling_result["chunks"]]
        embeddings = call_pinecone_for_embeddings(texts)
        
        # Add embeddings to chunks
        chunks_with_embeddings = []
        for i, chunk in enumerate(docling_result["chunks"]):
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding['id'] = hashlib.md5(chunk['text'].encode()).hexdigest()
            chunk_with_embedding['embedding'] = embeddings[i]
            chunks_with_embeddings.append(chunk_with_embedding)
        
        # Step 4: Store chunks to DynamoDB
        logger.info("💾 Step 4: Storing chunks to DynamoDB")
        dynamodb_success = store_chunks_to_dynamodb(chunks_with_embeddings, document_id, filename)
        
        # Step 5: Store embeddings to Pinecone using library
        logger.info("🔍 Step 5: Storing embeddings to Pinecone using library")
        pinecone_vectors = []
        for chunk in chunks_with_embeddings:
            pinecone_vectors.append({
                'id': chunk['id'],
                'values': chunk['embedding'],
                'metadata': {
                    'document_id': document_id,
                    'text': chunk['text'],
                    'type': chunk['type'],
                    'page': chunk.get('page')
                }
            })
        
        pinecone_result = call_pinecone_library(pinecone_vectors, 'upsert', 'default')
        pinecone_success = pinecone_result.get('success', False)
        
        # Step 6: Store relations to Neo4j using library
        logger.info("🕸️ Step 6: Storing relations to Neo4j using library")
        neo4j_query = """
        MERGE (d:Document {id: $document_id, filename: $filename})
        SET d.created_at = datetime()
        WITH d
        UNWIND $chunks as chunk
        MERGE (c:Chunk {id: chunk.id})
        SET c.text = chunk.text, c.type = chunk.type, c.page = chunk.page
        MERGE (d)-[:CONTAINS]->(c)
        """
        
        neo4j_parameters = {
            'document_id': document_id,
            'filename': filename,
            'chunks': chunks_with_embeddings
        }
        
        neo4j_result = call_neo4j_library(neo4j_query, neo4j_parameters, 'write')
        neo4j_success = neo4j_result.get('success', False)
        
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
        
        logger.info(f"🎉 Document processing pipeline completed successfully in {processing_time:.2f}s")
        logger.info(f"📊 Final stats: {result['chunks_processed']} chunks, {result['embeddings_generated']} embeddings")
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 Document processing pipeline failed after {processing_time:.2f}s: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
            "filename": filename,
            "processing_time": processing_time
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for S3-triggered document processing - BUSINESS LOGIC"""
    logger.info("=== DOCUMENT PROCESSOR BUSINESS LOGIC STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Handle S3 event
        records = event.get('Records', [])
        if not records:
            logger.warning("⚠️ No S3 records found in event")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": "No S3 records found in event"
                })
            }
        
        record = records[0]
        s3_info = record.get('s3', {})
        bucket = s3_info.get('bucket', {}).get('name', '')
        key = s3_info.get('object', {}).get('key', '')
        
        if not bucket or not key:
            logger.warning("⚠️ Invalid S3 event data")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": "Invalid S3 event data"
                })
            }
        
        logger.info(f"📁 Processing document from S3: s3://{bucket}/{key}")
        
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
            if document_id:
                logger.info(f"📋 Found document ID in metadata: {document_id}")
        except:
            pass
        
        # If no document ID in metadata, extract from S3 key path
        if not document_id:
            path_parts = key.split('/')
            if len(path_parts) >= 3 and path_parts[0] == 'documents':
                document_id = path_parts[2]  # documents/YYYY/MM/DD/{document_id}/filename
                logger.info(f"📋 Extracted document ID from S3 key: {document_id}")
        
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
        logger.error(f"💥 Error in document processor business logic: {e}")
        
        # Log error to centralized system
        log_error(
            'document-processor-business-logic',
            e,
            context,
            {
                'operation_type': event.get('operation_type', 'unknown'),
                'event_keys': list(event.keys()) if event else [],
                'function_name': 'document-processor-business-logic'
            },
            'CRITICAL'
        )
        
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
                "error_type": type(e).__name__
            })
        }
