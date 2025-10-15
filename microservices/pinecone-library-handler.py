#!/usr/bin/env python3
"""
Pinecone MCP Server Handler - Docker Lambda
Communicates with Pinecone MCP server instead of direct library usage
All business logic happens in Zip Lambdas
"""

import json
import os
import logging
import traceback
import sys
import time
import requests
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure

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

# MCP Server Configuration
# MCP Server URL will be auto-generated from Lambda function URL
def get_pinecone_mcp_url():
    """Get the Pinecone MCP server URL from Lambda function URL"""
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_url_config(FunctionName='pinecone-mcp-server')
        return response['FunctionUrl']
    except Exception as e:
        logger.warning(f"Could not get Pinecone MCP URL: {e}")
        return 'http://localhost:3000'  # Fallback for local development

PINECONE_MCP_SERVER_TIMEOUT = 300

# Initialize MCP Server connection
try:
    # Test connection to Pinecone MCP server
    pinecone_url = get_pinecone_mcp_url()
    logger.info(f"🔄 Connecting to Pinecone MCP server at {pinecone_url}")
    
    # Health check
    health_response = requests.get(f"{pinecone_url}/health", timeout=10)
    if health_response.status_code == 200:
        logger.info("✅ Pinecone MCP server is healthy and ready")
        MCP_SERVER_AVAILABLE = True
    else:
        logger.warning(f"⚠️ Pinecone MCP server health check failed: {health_response.status_code}")
        MCP_SERVER_AVAILABLE = False
    
    # Export MCP server configuration for use by Zip Lambdas
    PINECONE_MCP_CONFIG = {
        "server_url": get_pinecone_mcp_url(),
        "timeout": PINECONE_MCP_SERVER_TIMEOUT,
        "available": MCP_SERVER_AVAILABLE
    }
    
except Exception as e:
    logger.error(f"❌ Failed to connect to Pinecone MCP server: {e}")
    logger.error(f"📊 Error details: {str(e)}")
    PINECONE_MCP_CONFIG = {
        "server_url": get_pinecone_mcp_url(),
        "timeout": PINECONE_MCP_SERVER_TIMEOUT,
        "available": False
    }

def vector_search_with_mcp(query_vector: list, limit: int = 10, filter_dict: dict = None, namespace: str = 'default') -> dict:
    """Perform vector search using Pinecone MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🔍 Starting vector search with Pinecone MCP server")
        logger.info(f"📊 Query vector dimensions: {len(query_vector) if query_vector else 0}")
        logger.info(f"📊 Limit: {limit}")
        logger.info(f"📊 Namespace: {namespace}")
        logger.info(f"📊 Filter: {filter_dict}")
        logger.info(f"📊 MCP server URL: {get_pinecone_mcp_url()}")
        logger.info(f"📊 Timeout: {PINECONE_MCP_SERVER_TIMEOUT}s")
        
        # Validate input parameters
        if not query_vector or not isinstance(query_vector, list):
            raise ValueError("Query vector must be a non-empty list")
        
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Limit must be a positive integer")
        
        if limit > 1000:  # Pinecone limit
            raise ValueError("Limit cannot exceed 1000")
        
        # Prepare MCP request payload
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "pinecone/query",
            "params": {
                "vector": query_vector,
                "top_k": limit,
                "filter": filter_dict or {},
                "namespace": namespace,
                "include_metadata": True,
                "include_values": False  # Don't return vectors to save bandwidth
            }
        }
        
        logger.info(f"📊 MCP payload size: {len(json.dumps(mcp_payload))} characters")
        
        # Send request to MCP server with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Sending vector search request to MCP server (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{get_pinecone_mcp_url()}/mcp",
                    json=mcp_payload,
                    timeout=PINECONE_MCP_SERVER_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "KnowledgeBot-PineconeHandler/1.0"
                    }
                )
                
                logger.info(f"📊 Response status: {response.status_code}")
                logger.info(f"📊 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📊 Response keys: {list(result.keys())}")
                    
                    if "result" in result:
                        processing_time = (datetime.now() - start_time).total_seconds()
                        pinecone_result = result["result"]
                        matches = pinecone_result.get("matches", [])
                        result_namespace = pinecone_result.get("namespace", namespace)
                        
                        logger.info(f"✅ Vector search completed successfully by Pinecone MCP server")
                        logger.info(f"📊 Processing time: {processing_time:.3f}s")
                        logger.info(f"📊 Matches found: {len(matches)}")
                        logger.info(f"📊 Namespace: {result_namespace}")
                        
                        # Log success to centralized error logger
                        log_custom_error(
                            'pinecone-library-handler',
                            'vector_search_success',
                            {
                                'query_vector_dimensions': len(query_vector),
                                'limit': limit,
                                'namespace': namespace,
                                'matches_found': len(matches),
                                'processing_time': processing_time
                            },
                            'INFO'
                        )
                        
                        return {
                            "success": True,
                            "matches": matches,
                            "namespace": result_namespace,
                            "processing_time": processing_time
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown MCP server error")
                        logger.error(f"❌ MCP server returned error: {error_msg}")
                        log_error(
                            'pinecone-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'query_vector_dimensions': len(query_vector),
                                'limit': limit,
                                'namespace': namespace,
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
                            'pinecone-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'query_vector_dimensions': len(query_vector),
                                'limit': limit,
                                'namespace': namespace,
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
                    logger.error(f"❌ Pinecone MCP server request timed out after {max_retries} attempts")
                    log_error(
                        'pinecone-library-handler',
                        te,
                        None,
                        {
                            'query_vector_dimensions': len(query_vector),
                            'limit': limit,
                            'namespace': namespace,
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
                    logger.error(f"❌ Failed to connect to Pinecone MCP server after {max_retries} attempts")
                    log_error(
                        'pinecone-library-handler',
                        ce,
                        None,
                        {
                            'query_vector_dimensions': len(query_vector),
                            'limit': limit,
                            'namespace': namespace,
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
                    logger.error(f"❌ Error performing vector search with MCP server: {e}")
                    logger.error(f"📊 Error type: {type(e).__name__}")
                    logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                    
                    log_error(
                        'pinecone-library-handler',
                        e,
                        None,
                        {
                            'query_vector_dimensions': len(query_vector),
                            'limit': limit,
                            'namespace': namespace,
                            'processing_time': processing_time,
                            'error_type': type(e).__name__
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": str(e)}
            
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error in vector search: {ve}")
        log_error(
            'pinecone-library-handler',
            ve,
            None,
            {
                'query_vector_dimensions': len(query_vector) if query_vector else 0,
                'limit': limit,
                'namespace': namespace,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        return {"success": False, "error": str(ve)}
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Unexpected error in vector search: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'pinecone-library-handler',
            e,
            None,
            {
                'query_vector_dimensions': len(query_vector) if query_vector else 0,
                'limit': limit,
                'namespace': namespace,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        return {"success": False, "error": str(e)}

def upsert_vectors_with_mcp(vectors: list, namespace: str = 'default') -> dict:
    """Upsert vectors using Pinecone MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    
    try:
        logger.info(f"📤 Starting vector upsert with Pinecone MCP server")
        logger.info(f"📊 Vectors count: {len(vectors)}")
        logger.info(f"📊 Namespace: {namespace}")
        logger.info(f"📊 MCP server URL: {get_pinecone_mcp_url()}")
        logger.info(f"📊 Timeout: {PINECONE_MCP_SERVER_TIMEOUT}s")
        
        # Validate input parameters
        if not vectors or not isinstance(vectors, list):
            raise ValueError("Vectors must be a non-empty list")
        
        if len(vectors) == 0:
            raise ValueError("Vectors list cannot be empty")
        
        if len(vectors) > 100:  # Pinecone batch limit
            raise ValueError("Cannot upsert more than 100 vectors at once")
        
        # Validate vector structure
        for i, vector in enumerate(vectors):
            if not isinstance(vector, dict):
                raise ValueError(f"Vector {i} must be a dictionary")
            if 'id' not in vector or 'values' not in vector:
                raise ValueError(f"Vector {i} must have 'id' and 'values' fields")
            if not isinstance(vector['values'], list) or len(vector['values']) == 0:
                raise ValueError(f"Vector {i} values must be a non-empty list")
        
        # Prepare MCP request payload
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "pinecone/upsert",
            "params": {
                "vectors": vectors,
                "namespace": namespace
            }
        }
        
        logger.info(f"📊 MCP payload size: {len(json.dumps(mcp_payload))} characters")
        
        # Send request to MCP server with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Sending upsert request to MCP server (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{get_pinecone_mcp_url()}/mcp",
                    json=mcp_payload,
                    timeout=PINECONE_MCP_SERVER_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "KnowledgeBot-PineconeHandler/1.0"
                    }
                )
                
                logger.info(f"📊 Response status: {response.status_code}")
                logger.info(f"📊 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📊 Response keys: {list(result.keys())}")
                    
                    if "result" in result:
                        processing_time = (datetime.now() - start_time).total_seconds()
                        pinecone_result = result["result"]
                        upserted_count = pinecone_result.get("upserted_count", len(vectors))
                        
                        logger.info(f"✅ Vectors upserted successfully by Pinecone MCP server")
                        logger.info(f"📊 Processing time: {processing_time:.3f}s")
                        logger.info(f"📊 Vectors upserted: {upserted_count}")
                        logger.info(f"📊 Namespace: {namespace}")
                        
                        # Log success to centralized error logger
                        log_custom_error(
                            'pinecone-library-handler',
                            'vector_upsert_success',
                            {
                                'vectors_count': len(vectors),
                                'namespace': namespace,
                                'upserted_count': upserted_count,
                                'processing_time': processing_time
                            },
                            'INFO'
                        )
                        
                        return {
                            "success": True,
                            "upserted_count": upserted_count,
                            "processing_time": processing_time
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown MCP server error")
                        logger.error(f"❌ MCP server returned error: {error_msg}")
                        log_error(
                            'pinecone-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'vectors_count': len(vectors),
                                'namespace': namespace,
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
                            'pinecone-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'vectors_count': len(vectors),
                                'namespace': namespace,
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
                    logger.error(f"❌ Pinecone MCP server request timed out after {max_retries} attempts")
                    log_error(
                        'pinecone-library-handler',
                        te,
                        None,
                        {
                            'vectors_count': len(vectors),
                            'namespace': namespace,
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
                    logger.error(f"❌ Failed to connect to Pinecone MCP server after {max_retries} attempts")
                    log_error(
                        'pinecone-library-handler',
                        ce,
                        None,
                        {
                            'vectors_count': len(vectors),
                            'namespace': namespace,
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
                    logger.error(f"❌ Error upserting vectors with MCP server: {e}")
                    logger.error(f"📊 Error type: {type(e).__name__}")
                    logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                    
                    log_error(
                        'pinecone-library-handler',
                        e,
                        None,
                        {
                            'vectors_count': len(vectors),
                            'namespace': namespace,
                            'processing_time': processing_time,
                            'error_type': type(e).__name__
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": str(e)}
            
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error in vector upsert: {ve}")
        log_error(
            'pinecone-library-handler',
            ve,
            None,
            {
                'vectors_count': len(vectors) if vectors else 0,
                'namespace': namespace,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        return {"success": False, "error": str(ve)}
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Unexpected error in vector upsert: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'pinecone-library-handler',
            e,
            None,
            {
                'vectors_count': len(vectors) if vectors else 0,
                'namespace': namespace,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        return {"success": False, "error": str(e)}

def generate_embeddings_with_mcp(texts: list) -> dict:
    """Generate embeddings using Pinecone MCP server with native models and comprehensive logging"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🧠 Starting embedding generation with Pinecone MCP server using native models")
        logger.info(f"📊 Texts count: {len(texts)}")
        logger.info(f"📊 MCP server URL: {get_pinecone_mcp_url()}")
        logger.info(f"📊 Timeout: {PINECONE_MCP_SERVER_TIMEOUT}s")
        
        # Validate input parameters
        if not texts or not isinstance(texts, list):
            raise ValueError("Texts must be a non-empty list")
        
        if len(texts) == 0:
            raise ValueError("Texts list cannot be empty")
        
        if len(texts) > 100:  # Reasonable batch limit
            raise ValueError("Cannot process more than 100 texts at once")
        
        # Validate text content
        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError(f"Text {i} must be a string")
            if len(text.strip()) == 0:
                raise ValueError(f"Text {i} cannot be empty")
            if len(text) > 10000:  # Reasonable text length limit
                raise ValueError(f"Text {i} is too long (max 10000 characters)")
        
        # Prepare MCP request payload
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "pinecone/generate_embeddings",
            "params": {
                "texts": texts
            }
        }
        
        logger.info(f"📊 MCP payload size: {len(json.dumps(mcp_payload))} characters")
        
        # Send request to MCP server with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Sending embedding generation request to MCP server (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{get_pinecone_mcp_url()}/mcp",
                    json=mcp_payload,
                    timeout=PINECONE_MCP_SERVER_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "KnowledgeBot-PineconeHandler/1.0"
                    }
                )
                
                logger.info(f"📊 Response status: {response.status_code}")
                logger.info(f"📊 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📊 Response keys: {list(result.keys())}")
                    
                    if "result" in result:
                        processing_time = (datetime.now() - start_time).total_seconds()
                        pinecone_result = result["result"]
                        embeddings = pinecone_result.get("embeddings", [])
                        texts_processed = pinecone_result.get("texts_processed", len(texts))
                        method = pinecone_result.get("method", "pinecone_native")
                        
                        logger.info(f"✅ Embeddings generated successfully by Pinecone MCP server using native models")
                        logger.info(f"📊 Processing time: {processing_time:.3f}s")
                        logger.info(f"📊 Texts processed: {texts_processed}")
                        logger.info(f"📊 Embeddings generated: {len(embeddings)}")
                        logger.info(f"📊 Method: {method}")
                        
                        # Log success to centralized error logger
                        log_custom_error(
                            'pinecone-library-handler',
                            'embedding_generation_success',
                            {
                                'texts_count': len(texts),
                                'texts_processed': texts_processed,
                                'embeddings_generated': len(embeddings),
                                'method': method,
                                'processing_time': processing_time
                            },
                            'INFO'
                        )
                        
                        return {
                            "success": True,
                            "embeddings": embeddings,
                            "texts_processed": texts_processed,
                            "method": method,
                            "processing_time": processing_time
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown MCP server error")
                        logger.error(f"❌ MCP server returned error: {error_msg}")
                        log_error(
                            'pinecone-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'texts_count': len(texts),
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
                            'pinecone-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'texts_count': len(texts),
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
                    logger.error(f"❌ Pinecone MCP server request timed out after {max_retries} attempts")
                    log_error(
                        'pinecone-library-handler',
                        te,
                        None,
                        {
                            'texts_count': len(texts),
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
                    logger.error(f"❌ Failed to connect to Pinecone MCP server after {max_retries} attempts")
                    log_error(
                        'pinecone-library-handler',
                        ce,
                        None,
                        {
                            'texts_count': len(texts),
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
                    logger.error(f"❌ Error generating embeddings with MCP server: {e}")
                    logger.error(f"📊 Error type: {type(e).__name__}")
                    logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                    
                    log_error(
                        'pinecone-library-handler',
                        e,
                        None,
                        {
                            'texts_count': len(texts),
                            'processing_time': processing_time,
                            'error_type': type(e).__name__
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": str(e)}
            
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error in embedding generation: {ve}")
        log_error(
            'pinecone-library-handler',
            ve,
            None,
            {
                'texts_count': len(texts) if texts else 0,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        return {"success": False, "error": str(ve)}
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Unexpected error in embedding generation: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'pinecone-library-handler',
            e,
            None,
            {
                'texts_count': len(texts) if texts else 0,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        return {"success": False, "error": str(e)}

def lambda_handler(event, context):
    """Pinecone MCP Server Handler - Performs vector operations via MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== PINECONE MCP SERVER HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Validate MCP server availability
        if not PINECONE_MCP_CONFIG["available"]:
            logger.error("❌ Pinecone MCP server not available - connection failed")
            log_service_failure(
                'pinecone-library-handler',
                'MCP server not available',
                {
                    'request_id': request_id,
                    'server_url': PINECONE_MCP_CONFIG['server_url'],
                    'available': PINECONE_MCP_CONFIG['available']
                },
                'ERROR'
            )
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Pinecone MCP server not available - connection failed during container startup",
                    "request_id": request_id
                })
            }
        
        logger.info(f"✅ Pinecone MCP server available: {PINECONE_MCP_CONFIG['server_url']}")
        
        # Parse the request - handle both direct event and body-wrapped formats
        logger.info(f"📊 Parsing request...")
        
        try:
            # Check if operation_type is directly in the event (Lambda invocation format)
            if 'operation_type' in event:
                logger.info(f"✅ Found 'operation_type' directly in event")
                body = event
            # Check if operation_type is in the body field (API Gateway format)
            elif isinstance(event.get('body'), str):
                try:
                    body = json.loads(event['body'])
                    logger.info(f"✅ Successfully parsed JSON body")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"📊 Raw body: {event.get('body')}")
                    raise ValueError(f"Invalid JSON in request body: {e}")
            else:
                body = event.get('body', {})
                logger.info(f"✅ Using direct body object")
            
            logger.info(f"📊 Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'Not a dict'}")
            
        except ValueError as ve:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Request parsing error: {ve}")
            log_error(
                'pinecone-library-handler',
                ve,
                context,
                {
                    'request_id': request_id,
                    'processing_time': processing_time,
                    'error_type': 'RequestParsingError'
                },
                'WARNING'
            )
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": str(ve),
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Check operation type and route to appropriate MCP function
        operation_type = body.get('operation_type', 'status')
        logger.info(f"📊 Operation type: {operation_type}")
        
        if operation_type == 'search':
            logger.info(f"🔧 Processing vector search request via MCP server")
            query_vector = body.get('query_vector', [])
            limit = body.get('limit', 10)
            filter_dict = body.get('filter_dict', {})
            namespace = body.get('namespace', 'default')
            
            logger.info(f"📝 Query vector dimensions: {len(query_vector)}")
            logger.info(f"📝 Limit: {limit}")
            logger.info(f"📝 Filter: {filter_dict}")
            logger.info(f"📝 Namespace: {namespace}")
            
            # Perform vector search with MCP server
            result = vector_search_with_mcp(query_vector, limit, filter_dict, namespace)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"📊 Total processing time: {processing_time:.3f}s")
            
            # Add processing time to result
            if isinstance(result, dict):
                result["processing_time"] = processing_time
                result["request_id"] = request_id
            
            return {
                "statusCode": 200 if result["success"] else 500,
                "body": json.dumps({
                    "success": result["success"],
                    "results": {
                        "matches": result.get("matches", []),
                        "namespace": result.get("namespace", namespace)
                    } if result["success"] else None,
                    "error": result.get("error") if not result["success"] else None,
                    "processing_time": processing_time,
                    "request_id": request_id
                })
            }
            
        elif operation_type == 'upsert':
            logger.info(f"📤 Processing vector upsert request via MCP server")
            vectors = body.get('vectors', [])
            namespace = body.get('namespace', 'default')
            
            logger.info(f"📝 Vectors count: {len(vectors)}")
            logger.info(f"📝 Namespace: {namespace}")
            
            # Perform vector upsert with MCP server
            result = upsert_vectors_with_mcp(vectors, namespace)
            
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
            
        elif operation_type == 'generate_embeddings':
            logger.info(f"🧠 Processing embedding generation request via MCP server")
            texts = body.get('texts', [])
            
            logger.info(f"📝 Texts count: {len(texts)}")
            
            # Generate embeddings with MCP server
            result = generate_embeddings_with_mcp(texts)
            
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
            # Return MCP server status
            logger.info(f"📊 No specific operation found, returning MCP server status")
            processing_time = (datetime.now() - start_time).total_seconds()
            status_info = {
                "success": True,
                "message": "Pinecone MCP server is ready",
                "server_url": PINECONE_MCP_CONFIG["server_url"],
                "available": PINECONE_MCP_CONFIG["available"],
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Status response: {status_info}")
            return {
                "statusCode": 200,
                "body": json.dumps(status_info)
            }
        
    except json.JSONDecodeError as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ JSON decode error in Pinecone MCP handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'pinecone-library-handler',
            e,
            context,
            {
                'request_id': request_id,
                'processing_time': processing_time,
                'error_type': 'JSONDecodeError'
            },
            'ERROR'
        )
        
        return {
            "statusCode": 400,
            "body": json.dumps({
                "success": False,
                "error": f"Invalid JSON in request: {e}",
                "error_type": "JSONDecodeError",
                "request_id": request_id,
                "processing_time": processing_time
            })
        }
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error in Pinecone MCP server handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'pinecone-library-handler',
            e,
            context,
            {
                'request_id': request_id,
                'operation_type': event.get('operation_type', 'unknown'),
                'event_keys': list(event.keys()) if event else [],
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
                "error_type": type(e).__name__,
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            })
        }
