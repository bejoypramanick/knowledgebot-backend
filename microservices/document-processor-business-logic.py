#!/usr/bin/env python3
"""
Document Processor Business Logic - Zip Lambda
Orchestrates document processing using Universal MCP Client
Handles S3 events and coordinates MCP servers for document processing
"""

import json
import logging
import boto3
import base64
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import Universal MCP Client
from mcp_client import UniversalMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS clients
s3_client = boto3.client('s3')

async def process_document_with_mcp(document_bytes: bytes, filename: str, bucket: str) -> Dict[str, Any]:
    """
    Process document using MCP servers
    """
    try:
        async with UniversalMCPClient() as mcp_client:
            logger.info(f"🚀 Starting document processing for: {filename}")
            
            # Step 1: Process document with Docling MCP Server
            logger.info("📄 Processing document with Docling MCP Server")
            docling_result = await mcp_client.docling_process_document(
                content=base64.b64encode(document_bytes).decode('utf-8'),
                options={"filename": filename}
            )
            
            if not docling_result.get("success", False):
                raise Exception(f"Docling processing failed: {docling_result.get('error', 'Unknown error')}")
            
            # Extract processed content and chunks
            processed_content = docling_result.get("content", "")
            chunks = docling_result.get("chunks", [])
            
            logger.info(f"✅ Docling processed successfully: {len(chunks)} chunks")
            
            # Step 2: Store markdown to S3
            logger.info("💾 Storing markdown to S3")
            markdown_key = f"processed/{filename.replace('.pdf', '.md')}"
            s3_client.put_object(
                Bucket=bucket,
                Key=markdown_key,
                Body=processed_content,
                ContentType='text/markdown'
            )
            
            # Step 3: Process chunks with Pinecone MCP Server
            logger.info("🔍 Processing chunks with Pinecone MCP Server")
            pinecone_records = []
            for i, chunk in enumerate(chunks):
                record = {
                    "id": f"{filename}_{i}",
                    "values": chunk.get("embedding", []),  # Docling should provide embeddings
                    "metadata": {
                        "filename": filename,
                        "chunk_index": i,
                        "text": chunk.get("text", ""),
                        "processed_at": datetime.now().isoformat()
                    }
                }
                pinecone_records.append(record)
            
            # Upsert to Pinecone
            pinecone_result = await mcp_client.pinecone_upsert(
                index_name="knowledgebot-index",
                records=pinecone_records
            )
            
            if not pinecone_result.get("success", False):
                raise Exception(f"Pinecone upsert failed: {pinecone_result.get('error', 'Unknown error')}")
            
            logger.info(f"✅ Pinecone upsert successful: {len(pinecone_records)} records")
            
            # Step 4: Store chunks to DynamoDB via MCP Server
            logger.info("💾 Storing chunks to DynamoDB via MCP Server")
            for i, chunk in enumerate(chunks):
                dynamodb_item = {
                    "document_id": filename,
                    "chunk_id": f"{filename}_{i}",
                    "text": chunk.get("text", ""),
                    "metadata": chunk.get("metadata", {}),
                    "processed_at": datetime.now().isoformat(),
                    "markdown_key": markdown_key
                }
                
                dynamodb_result = await mcp_client.dynamodb_put_item(
                    table_name="document-chunks",
                    item=dynamodb_item
                )
                
                if not dynamodb_result.get("success", False):
                    logger.warning(f"DynamoDB put failed for chunk {i}: {dynamodb_result.get('error', 'Unknown error')}")
            
            logger.info(f"✅ DynamoDB storage completed: {len(chunks)} chunks")
            
            # Step 5: Create graph relations with Neo4j MCP Server
            logger.info("🕸️ Creating graph relations with Neo4j MCP Server")
            
            # Create document node
            document_cypher = """
            MERGE (d:Document {id: $document_id, filename: $filename, processed_at: $processed_at})
            SET d.markdown_key = $markdown_key
            """
            
            neo4j_result = await mcp_client.neo4j_execute_query(
                cypher=document_cypher,
                parameters={
                    "document_id": filename,
                    "filename": filename,
                    "processed_at": datetime.now().isoformat(),
                    "markdown_key": markdown_key
                }
            )
            
            if not neo4j_result.get("success", False):
                logger.warning(f"Neo4j document node creation failed: {neo4j_result.get('error', 'Unknown error')}")
            
            # Create chunk nodes and relationships
            for i, chunk in enumerate(chunks):
                chunk_cypher = """
                MATCH (d:Document {id: $document_id})
                MERGE (c:Chunk {id: $chunk_id, document_id: $document_id, chunk_index: $chunk_index})
                SET c.text = $text, c.processed_at = $processed_at
                MERGE (d)-[:CONTAINS]->(c)
                """
                
                neo4j_result = await mcp_client.neo4j_execute_query(
                    cypher=chunk_cypher,
                    parameters={
                        "document_id": filename,
                        "chunk_id": f"{filename}_{i}",
                        "chunk_index": i,
                        "text": chunk.get("text", ""),
                        "processed_at": datetime.now().isoformat()
                    }
                )
                
                if not neo4j_result.get("success", False):
                    logger.warning(f"Neo4j chunk node creation failed for chunk {i}: {neo4j_result.get('error', 'Unknown error')}")
            
            logger.info(f"✅ Neo4j graph relations created: {len(chunks)} chunks")
            
            return {
                "success": True,
                "filename": filename,
                "chunks_processed": len(chunks),
                "markdown_key": markdown_key,
                "pinecone_records": len(pinecone_records),
                "dynamodb_chunks": len(chunks),
                "neo4j_relations": len(chunks) + 1  # document + chunks
            }
            
    except Exception as e:
        logger.error(f"❌ Document processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "filename": filename
        }

def lambda_handler(event, context):
    """
    AWS Lambda handler for document processing
    """
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== DOCUMENT PROCESSOR BUSINESS LOGIC STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event: {json.dumps(event, default=str)}")
    
    try:
        # Parse S3 event
        if 'Records' in event:
            for record in event['Records']:
                if record['eventName'].startswith('ObjectCreated'):
                    bucket = record['s3']['bucket']['name']
                    key = record['s3']['object']['key']
                    
                    logger.info(f"📄 Processing S3 event: {bucket}/{key}")
                    
                    # Download document from S3
                    logger.info("📥 Downloading document from S3")
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    document_bytes = response['Body'].read()
                    
                    # Process document with MCP servers
                    result = asyncio.run(process_document_with_mcp(document_bytes, key, bucket))
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.info(f"📊 Total processing time: {processing_time:.3f}s")
                    
                    # Add processing time to result
                    if isinstance(result, dict):
                        result["processing_time"] = processing_time
                        result["request_id"] = request_id
                    
                    return {
                        "statusCode": 200 if result["success"] else 500,
                        "body": json.dumps(result)
                    }
        
        # Handle direct document processing requests
        elif 'document_bytes' in event and 'filename' in event:
            logger.info("📄 Processing direct document request")
            
            # Decode document bytes if they're base64 encoded
            if isinstance(event["document_bytes"], str):
                document_bytes = base64.b64decode(event["document_bytes"])
            else:
                document_bytes = event["document_bytes"]
            
            # Process document with MCP servers
            result = asyncio.run(process_document_with_mcp(
                document_bytes, 
                event["filename"], 
                event.get("bucket", "knowledgebot-documents")
            ))
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"📊 Total processing time: {processing_time:.3f}s")
            
            # Add processing time to result
            if isinstance(result, dict):
                result["processing_time"] = processing_time
                result["request_id"] = request_id
            
            return {
                "statusCode": 200 if result["success"] else 500,
                "body": json.dumps(result)
            }
        
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": "Invalid event format. Expected S3 event or document processing request.",
                    "request_id": request_id
                })
            }
            
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Lambda handler error: {e}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "request_id": request_id
            })
        }
