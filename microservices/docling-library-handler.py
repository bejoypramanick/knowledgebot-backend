#!/usr/bin/env python3
"""
Docling MCP Server Handler - Docker Lambda
Communicates with Docling MCP server using MCP protocol
All business logic happens in Zip Lambdas
"""

import json
import logging
import traceback
import sys
import asyncio
import base64
import os
import time
import requests
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure

# MCP imports
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

# Configure logging with detailed format
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

# MCP Server Configuration
# MCP Server URL will be auto-generated from Lambda function URL
def get_docling_mcp_url():
    """Get the Docling MCP server URL from Lambda function URL"""
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_url_config(FunctionName='docling-mcp-server')
        return response['FunctionUrl']
    except Exception as e:
        logger.warning(f"Could not get Docling MCP URL: {e}")
        return 'http://localhost:3000'  # Fallback for local development

DOCLING_MCP_SERVER_TIMEOUT = 300

# Initialize MCP Server connection
try:
    docling_url = get_docling_mcp_url()
    logger.info(f"🔄 Initializing Docling MCP server connection")
    logger.info(f"📊 MCP server URL: {docling_url}")
    logger.info(f"📊 Timeout: {DOCLING_MCP_SERVER_TIMEOUT}s")
    
    # Export MCP server configuration for use by Zip Lambdas
    DOCLING_MCP_CONFIG = {
        "server_url": docling_url,
        "timeout": DOCLING_MCP_SERVER_TIMEOUT,
        "available": True
    }
    logger.info("✅ Docling MCP server configuration ready")

except Exception as e:
    logger.error(f"❌ Failed to initialize Docling MCP server: {e}")
    logger.error(f"📊 Error details: {str(e)}")
    DOCLING_MCP_CONFIG = {
        "server_url": get_docling_mcp_url(),
        "timeout": DOCLING_MCP_SERVER_TIMEOUT,
        "available": False
    }

def process_document_with_mcp(document_bytes: bytes, filename: str) -> dict:
    """Process document using Docling MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🔄 Starting document processing: {filename}")
        logger.info(f"📊 Document size: {len(document_bytes)} bytes")
        logger.info(f"📊 MCP server URL: {DOCLING_MCP_SERVER_URL}")
        logger.info(f"📊 Timeout: {DOCLING_MCP_SERVER_TIMEOUT}s")
        
        # Validate input parameters
        if not document_bytes or not isinstance(document_bytes, bytes):
            raise ValueError("Document bytes must be a non-empty bytes object")
        
        if not filename or not isinstance(filename, str):
            raise ValueError("Filename must be a non-empty string")
        
        # Check file size limits
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit for processing
        if len(document_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"Document too large: {len(document_bytes)} bytes (max: {MAX_FILE_SIZE})")
        
        # Encode document bytes to base64 for MCP server
        logger.info("🔄 Encoding document to base64")
        document_b64 = base64.b64encode(document_bytes).decode('utf-8')
        logger.info(f"📊 Base64 encoded size: {len(document_b64)} characters")
        
        # Prepare MCP request payload with optimized options
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "docling/process_document",
            "params": {
                "document_data": document_b64,
                "filename": filename,
                "options": {
                    "format": "markdown",
                    "include_metadata": True,
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "do_ocr": True,
                    "do_table_structure": True
                }
            }
        }
        
        logger.info(f"📊 MCP payload size: {len(json.dumps(mcp_payload))} characters")
        
        # Send request to MCP server with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Sending request to MCP server (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{DOCLING_MCP_SERVER_URL}/mcp",
                    json=mcp_payload,
                    timeout=DOCLING_MCP_SERVER_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "KnowledgeBot-DoclingHandler/1.0"
                    }
                )
                
                logger.info(f"📊 Response status: {response.status_code}")
                logger.info(f"📊 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📊 Response keys: {list(result.keys())}")
                    
                    if "result" in result:
                        processing_time = (datetime.now() - start_time).total_seconds()
                        
                        # Extract and validate result
                        docling_result = result["result"]
                        content = docling_result.get("content", {})
                        chunks = docling_result.get("chunks", [])
                        metadata = docling_result.get("metadata", {})
                        statistics = docling_result.get("statistics", {})
                        
                        logger.info(f"✅ Document processed successfully by Docling MCP server")
                        logger.info(f"📊 Processing time: {processing_time:.3f}s")
                        logger.info(f"📊 Chunks generated: {len(chunks)}")
                        logger.info(f"📊 Statistics: {statistics}")
                        
                        # Log success to centralized error logger
                        log_custom_error(
                            'docling-library-handler',
                            'document_processing_success',
                            {
                                'filename': filename,
                                'file_size': len(document_bytes),
                                'chunks_generated': len(chunks),
                                'processing_time': processing_time,
                                'statistics': statistics
                            },
                            'INFO'
                        )
                        
                        return {
                            "success": True,
                            "content": content,
                            "chunks": chunks,
                            "metadata": metadata,
                            "statistics": statistics,
                            "processing_time": processing_time
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown MCP server error")
                        logger.error(f"❌ MCP server returned error: {error_msg}")
                        log_error(
                            'docling-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'filename': filename,
                                'file_size': len(document_bytes),
                                'processing_time': (datetime.now() - start_time).total_seconds(),
                                'error_type': 'MCPError'
                            },
                            'ERROR'
                        )
                        return {"success": False, "error": error_msg}
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ MCP server request failed: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"🔄 Retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                    else:
                        log_error(
                            'docling-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'filename': filename,
                                'file_size': len(document_bytes),
                                'processing_time': (datetime.now() - start_time).total_seconds(),
                                'error_type': 'HTTPError'
                            },
                            'ERROR'
                        )
                        return {"success": False, "error": error_msg}
                        
            except requests.exceptions.Timeout as te:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ MCP server request timed out (attempt {attempt + 1}/{max_retries}): {te}")
                    time.sleep(2)
                    continue
                else:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.error(f"❌ Docling MCP server request timed out after {max_retries} attempts")
                    log_error(
                        'docling-library-handler',
                        te,
                        None,
                        {
                            'filename': filename,
                            'file_size': len(document_bytes),
                            'processing_time': processing_time,
                            'error_type': 'TimeoutError'
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": "MCP server request timed out"}
            
            except requests.exceptions.ConnectionError as ce:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Connection error (attempt {attempt + 1}/{max_retries}): {ce}")
                    time.sleep(2)
                    continue
                else:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.error(f"❌ Failed to connect to Docling MCP server after {max_retries} attempts")
                    log_error(
                        'docling-library-handler',
                        ce,
                        None,
                        {
                            'filename': filename,
                            'file_size': len(document_bytes),
                            'processing_time': processing_time,
                            'error_type': 'ConnectionError'
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": "Cannot connect to MCP server"}
            
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Request error (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2)
                    continue
                else:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.error(f"❌ Error processing document with MCP server: {e}")
                    logger.error(f"📊 Error type: {type(e).__name__}")
                    logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                    
                    log_error(
                        'docling-library-handler',
                        e,
                        None,
                        {
                            'filename': filename,
                            'file_size': len(document_bytes),
                            'processing_time': processing_time,
                            'error_type': type(e).__name__
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": str(e)}
            
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error processing document: {ve}")
        log_error(
            'docling-library-handler',
            ve,
            None,
            {
                'filename': filename,
                'file_size': len(document_bytes) if document_bytes else 0,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        return {"success": False, "error": str(ve)}
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Unexpected error processing document: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'docling-library-handler',
            e,
            None,
            {
                'filename': filename,
                'file_size': len(document_bytes) if document_bytes else 0,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        return {"success": False, "error": str(e)}

def lambda_handler(event, context):
    """Docling MCP Server Handler - Processes documents via MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== DOCLING MCP SERVER HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event keys: {list(event.keys()) if event else 'None'}")
    logger.info(f"📊 Context: {context}")
    
    try:
        # Validate MCP server availability
        if not DOCLING_MCP_CONFIG["available"]:
            logger.error("❌ Docling MCP server not available")
            log_service_failure(
                'docling-library-handler',
                'MCP server not available',
                {
                    'request_id': request_id,
                    'server_url': DOCLING_MCP_CONFIG["server_url"],
                    'available': DOCLING_MCP_CONFIG["available"]
                },
                'ERROR'
            )
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Docling MCP server not available",
                    "request_id": request_id
                })
            }
        
        # Check if this is a document processing request
        if "document_bytes" in event and "filename" in event:
            logger.info("📄 Processing document via MCP server")
            logger.info(f"📊 Filename: {event['filename']}")
            logger.info(f"📊 Document bytes type: {type(event['document_bytes'])}")
            
            try:
                # Decode document bytes if they're base64 encoded
                if isinstance(event["document_bytes"], str):
                    logger.info("🔄 Decoding base64 document bytes")
                    document_bytes = base64.b64decode(event["document_bytes"])
                    logger.info(f"📊 Decoded document size: {len(document_bytes)} bytes")
                else:
                    document_bytes = event["document_bytes"]
                    logger.info(f"📊 Document bytes size: {len(document_bytes)} bytes")
                
                # Validate document bytes
                if not document_bytes or len(document_bytes) == 0:
                    raise ValueError("Document bytes cannot be empty")
                
                # Process document with MCP server
                logger.info("🔄 Calling process_document_with_mcp")
                result = process_document_with_mcp(document_bytes, event["filename"])
                
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
                
            except ValueError as ve:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ Validation error in document processing: {ve}")
                log_error(
                    'docling-library-handler',
                    ve,
                    context,
                    {
                        'request_id': request_id,
                        'filename': event.get('filename', 'unknown'),
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": str(ve),
                        "request_id": request_id
                    })
                }
        else:
            # Return MCP server status
            logger.info("📊 Returning MCP server status")
            status_info = {
                "success": True,
                "message": "Docling MCP server is ready",
                "server_url": DOCLING_MCP_CONFIG["server_url"],
                "available": DOCLING_MCP_CONFIG["available"],
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Status response: {status_info}")
            return {
                "statusCode": 200,
                "body": json.dumps(status_info)
            }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error in Docling MCP server handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        # Log error to centralized system
        log_error(
            'docling-library-handler',
            e,
            context,
            {
                'request_id': request_id,
                'event': event,
                'processing_time': processing_time,
                'error_type': 'HandlerError'
            },
            'ERROR'
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "request_id": request_id,
                "processing_time": processing_time
            })
        }
