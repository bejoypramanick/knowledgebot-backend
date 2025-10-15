#!/usr/bin/env python3
"""
Neo4j MCP Server Handler - Docker Lambda
Communicates with Neo4j MCP server instead of direct library usage
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
def get_neo4j_mcp_url():
    """Get the Neo4j MCP server URL from Lambda function URL"""
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_url_config(FunctionName='neo4j-mcp-server')
        return response['FunctionUrl']
    except Exception as e:
        logger.warning(f"Could not get Neo4j MCP URL: {e}")
        return 'http://localhost:3000'  # Fallback for local development

NEO4J_MCP_SERVER_TIMEOUT = 300

# Initialize MCP Server connection
try:
    # Test connection to Neo4j MCP server
    neo4j_url = get_neo4j_mcp_url()
    logger.info(f"🔄 Connecting to Neo4j MCP server at {neo4j_url}")
    
    # Health check
    health_response = requests.get(f"{neo4j_url}/health", timeout=10)
    if health_response.status_code == 200:
        logger.info("✅ Neo4j MCP server is healthy and ready")
        MCP_SERVER_AVAILABLE = True
    else:
        logger.warning(f"⚠️ Neo4j MCP server health check failed: {health_response.status_code}")
        MCP_SERVER_AVAILABLE = False
    
    # Export MCP server configuration for use by Zip Lambdas
    NEO4J_MCP_CONFIG = {
        "server_url": get_neo4j_mcp_url(),
        "timeout": NEO4J_MCP_SERVER_TIMEOUT,
        "available": MCP_SERVER_AVAILABLE
    }
    
except Exception as e:
    logger.error(f"❌ Failed to connect to Neo4j MCP server: {e}")
    logger.error(f"📊 Error details: {str(e)}")
    NEO4J_MCP_CONFIG = {
        "server_url": get_neo4j_mcp_url(),
        "timeout": NEO4J_MCP_SERVER_TIMEOUT,
        "available": False
    }

def execute_cypher_with_mcp(cypher_query: str, parameters: dict = None, operation_type: str = "read") -> dict:
    """Execute Cypher query using Neo4j MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🔄 Starting {operation_type} query execution with Neo4j MCP server")
        logger.info(f"📊 Query: {cypher_query[:200]}{'...' if len(cypher_query) > 200 else ''}")
        logger.info(f"📊 Parameters: {parameters}")
        logger.info(f"📊 Operation type: {operation_type}")
        logger.info(f"📊 MCP server URL: {get_neo4j_mcp_url()}")
        logger.info(f"📊 Timeout: {NEO4J_MCP_SERVER_TIMEOUT}s")
        
        # Validate input parameters
        if not cypher_query or not isinstance(cypher_query, str):
            raise ValueError("Cypher query must be a non-empty string")
        
        if len(cypher_query.strip()) == 0:
            raise ValueError("Cypher query cannot be empty")
        
        if parameters is not None and not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary or None")
        
        if operation_type not in ["read", "write", "schema"]:
            raise ValueError("Operation type must be 'read', 'write', or 'schema'")
        
        # Prepare MCP request payload
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "neo4j/execute_cypher",
            "params": {
                "query": cypher_query,
                "parameters": parameters or {},
                "operation_type": operation_type
            }
        }
        
        logger.info(f"📊 MCP payload size: {len(json.dumps(mcp_payload))} characters")
        
        # Send request to MCP server with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Sending Cypher query to MCP server (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{get_neo4j_mcp_url()}/mcp",
                    json=mcp_payload,
                    timeout=NEO4J_MCP_SERVER_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "KnowledgeBot-Neo4jHandler/1.0"
                    }
                )
                
                logger.info(f"📊 Response status: {response.status_code}")
                logger.info(f"📊 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📊 Response keys: {list(result.keys())}")
                    
                    if "result" in result:
                        processing_time = (datetime.now() - start_time).total_seconds()
                        neo4j_result = result["result"]
                        data = neo4j_result.get("data", [])
                        summary = neo4j_result.get("summary", {})
                        stats = neo4j_result.get("stats", {})
                        
                        logger.info(f"✅ Cypher query executed successfully by Neo4j MCP server")
                        logger.info(f"📊 Processing time: {processing_time:.3f}s")
                        logger.info(f"📊 Records returned: {len(data)}")
                        logger.info(f"📊 Summary: {summary}")
                        logger.info(f"📊 Stats: {stats}")
                        
                        # Log success to centralized error logger
                        log_custom_error(
                            'neo4j-library-handler',
                            'cypher_query_success',
                            {
                                'query_length': len(cypher_query),
                                'operation_type': operation_type,
                                'parameters_count': len(parameters) if parameters else 0,
                                'records_returned': len(data),
                                'processing_time': processing_time
                            },
                            'INFO'
                        )
                        
                        return {
                            "success": True,
                            "data": data,
                            "summary": summary,
                            "stats": stats,
                            "processing_time": processing_time
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown MCP server error")
                        logger.error(f"❌ MCP server returned error: {error_msg}")
                        log_error(
                            'neo4j-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'query_length': len(cypher_query),
                                'operation_type': operation_type,
                                'parameters_count': len(parameters) if parameters else 0,
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
                            'neo4j-library-handler',
                            Exception(error_msg),
                            None,
                            {
                                'query_length': len(cypher_query),
                                'operation_type': operation_type,
                                'parameters_count': len(parameters) if parameters else 0,
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
                    logger.error(f"❌ Neo4j MCP server request timed out after {max_retries} attempts")
                    log_error(
                        'neo4j-library-handler',
                        te,
                        None,
                        {
                            'query_length': len(cypher_query),
                            'operation_type': operation_type,
                            'parameters_count': len(parameters) if parameters else 0,
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
                    logger.error(f"❌ Failed to connect to Neo4j MCP server after {max_retries} attempts")
                    log_error(
                        'neo4j-library-handler',
                        ce,
                        None,
                        {
                            'query_length': len(cypher_query),
                            'operation_type': operation_type,
                            'parameters_count': len(parameters) if parameters else 0,
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
                    logger.error(f"❌ Error executing Cypher query with MCP server: {e}")
                    logger.error(f"📊 Error type: {type(e).__name__}")
                    logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                    
                    log_error(
                        'neo4j-library-handler',
                        e,
                        None,
                        {
                            'query_length': len(cypher_query),
                            'operation_type': operation_type,
                            'parameters_count': len(parameters) if parameters else 0,
                            'processing_time': processing_time,
                            'error_type': type(e).__name__
                        },
                        'ERROR'
                    )
                    return {"success": False, "error": str(e)}
            
    except ValueError as ve:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Validation error in Cypher query execution: {ve}")
        log_error(
            'neo4j-library-handler',
            ve,
            None,
            {
                'query_length': len(cypher_query) if cypher_query else 0,
                'operation_type': operation_type,
                'parameters_count': len(parameters) if parameters else 0,
                'processing_time': processing_time,
                'error_type': 'ValidationError'
            },
            'WARNING'
        )
        return {"success": False, "error": str(ve)}
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Unexpected error in Cypher query execution: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'neo4j-library-handler',
            e,
            None,
            {
                'query_length': len(cypher_query) if cypher_query else 0,
                'operation_type': operation_type,
                'parameters_count': len(parameters) if parameters else 0,
                'processing_time': processing_time,
                'error_type': type(e).__name__
            },
            'ERROR'
        )
        return {"success": False, "error": str(e)}

def lambda_handler(event, context):
    """Neo4j MCP Server Handler - Executes Cypher queries via MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== NEO4J MCP SERVER HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Validate MCP server availability
        if not NEO4J_MCP_CONFIG["available"]:
            logger.error("❌ Neo4j MCP server not available - connection failed")
            log_service_failure(
                'neo4j-library-handler',
                'MCP server not available',
                {
                    'request_id': request_id,
                    'server_url': NEO4J_MCP_CONFIG['server_url'],
                    'available': NEO4J_MCP_CONFIG['available']
                },
                'ERROR'
            )
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Neo4j MCP server not available - connection failed during container startup",
                    "request_id": request_id
                })
            }
        
        logger.info(f"✅ Neo4j MCP server available: {NEO4J_MCP_CONFIG['server_url']}")
        
        # Check if this is a Cypher query request
        if "cypher_query" in event:
            logger.info("🔍 Executing Cypher query via MCP server")
            
            try:
                cypher_query = event["cypher_query"]
                parameters = event.get("parameters", {})
                operation_type = event.get("operation_type", "read")
                
                logger.info(f"📊 Query: {cypher_query[:200]}{'...' if len(cypher_query) > 200 else ''}")
                logger.info(f"📊 Parameters: {parameters}")
                logger.info(f"📊 Operation type: {operation_type}")
                
                # Validate input parameters
                if not cypher_query or not isinstance(cypher_query, str):
                    raise ValueError("Cypher query must be a non-empty string")
                
                if parameters is not None and not isinstance(parameters, dict):
                    raise ValueError("Parameters must be a dictionary or None")
                
                if operation_type not in ["read", "write", "schema"]:
                    raise ValueError("Operation type must be 'read', 'write', or 'schema'")
                
                # Execute query with MCP server
                result = execute_cypher_with_mcp(cypher_query, parameters, operation_type)
                
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
                logger.error(f"❌ Validation error in Cypher query request: {ve}")
                log_error(
                    'neo4j-library-handler',
                    ve,
                    context,
                    {
                        'request_id': request_id,
                        'cypher_query': event.get('cypher_query', 'unknown')[:100],
                        'operation_type': event.get('operation_type', 'unknown'),
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
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
        else:
            # Return MCP server status
            logger.info("📊 Returning MCP server status")
            processing_time = (datetime.now() - start_time).total_seconds()
            status_info = {
                "success": True,
                "message": "Neo4j MCP server is ready",
                "server_url": NEO4J_MCP_CONFIG["server_url"],
                "available": NEO4J_MCP_CONFIG["available"],
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Status response: {status_info}")
            return {
                "statusCode": 200,
                "body": json.dumps(status_info)
            }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error in Neo4j MCP server handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'neo4j-library-handler',
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
