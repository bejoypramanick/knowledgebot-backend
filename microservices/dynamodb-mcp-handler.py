#!/usr/bin/env python3
"""
DynamoDB MCP Handler Lambda
Handles DynamoDB operations via MCP server with comprehensive logging and error handling
"""

import json
import logging
import boto3
import os
import traceback
import time
import requests
from datetime import datetime
from typing import Dict, Any, List

# Import error logging utility
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AWS clients
lambda_client = boto3.client('lambda')

# Configuration
DYNAMODB_MCP_CONFIG = {
    "server_url": '',  # Will be auto-generated from Lambda function URL
    "timeout": 30,
    "available": False
}

def check_mcp_server_availability():
    """Check if DynamoDB MCP server is available"""
    try:
        if not DYNAMODB_MCP_CONFIG["server_url"]:
            logger.warning("⚠️ DynamoDB MCP server URL not configured")
            return False
        
        # Try to get health status
        response = requests.get(
            f"{DYNAMODB_MCP_CONFIG['server_url']}/health",
            timeout=5
        )
        
        if response.status_code == 200:
            DYNAMODB_MCP_CONFIG["available"] = True
            logger.info(f"✅ DynamoDB MCP server is available: {DYNAMODB_MCP_CONFIG['server_url']}")
            return True
        else:
            logger.warning(f"⚠️ DynamoDB MCP server returned status {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ DynamoDB MCP server not available: {e}")
        DYNAMODB_MCP_CONFIG["available"] = False
        return False

def call_dynamodb_mcp_server(operation: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call DynamoDB MCP server for operations"""
    try:
        logger.info(f"💾 Calling DynamoDB MCP server for {operation}")
        
        if not DYNAMODB_MCP_CONFIG["available"]:
            logger.error("❌ DynamoDB MCP server not available")
            return {
                "success": False,
                "error": "DynamoDB MCP server not available"
            }
        
        # Prepare MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": operation,
                "arguments": payload
            }
        }
        
        # Make request to MCP server
        response = requests.post(
            DYNAMODB_MCP_CONFIG["server_url"],
            json=mcp_request,
            timeout=DYNAMODB_MCP_CONFIG["timeout"],
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                # Parse MCP response
                content = result["result"].get("content", [])
                if content and len(content) > 0:
                    response_text = content[0].get("text", "")
                    try:
                        parsed_response = json.loads(response_text)
                        logger.info(f"✅ DynamoDB MCP server {operation} completed successfully")
                        return parsed_response
                    except json.JSONDecodeError:
                        logger.error(f"❌ Invalid JSON response from DynamoDB MCP server: {response_text}")
                        return {
                            "success": False,
                            "error": "Invalid response format from DynamoDB MCP server"
                        }
                else:
                    logger.error(f"❌ Empty response from DynamoDB MCP server")
                    return {
                        "success": False,
                        "error": "Empty response from DynamoDB MCP server"
                    }
            else:
                logger.error(f"❌ Error in DynamoDB MCP server response: {result}")
                return {
                    "success": False,
                    "error": f"DynamoDB MCP server error: {result.get('error', 'Unknown error')}"
                }
        else:
            logger.error(f"❌ DynamoDB MCP server returned status {response.status_code}: {response.text}")
            return {
                "success": False,
                "error": f"DynamoDB MCP server returned status {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"⏰ DynamoDB MCP server timeout after {DYNAMODB_MCP_CONFIG['timeout']}s")
        return {
            "success": False,
            "error": f"DynamoDB MCP server timeout after {DYNAMODB_MCP_CONFIG['timeout']}s"
        }
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Connection error to DynamoDB MCP server")
        return {
            "success": False,
            "error": "Connection error to DynamoDB MCP server"
        }
    except Exception as e:
        logger.error(f"❌ Error calling DynamoDB MCP server: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """DynamoDB MCP Handler - Performs DynamoDB operations via MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== DYNAMODB MCP HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Check MCP server availability
        check_mcp_server_availability()
        
        if not DYNAMODB_MCP_CONFIG["available"]:
            logger.error("❌ DynamoDB MCP server not available - connection failed")
            log_service_failure(
                'dynamodb-mcp-handler',
                'MCP server not available',
                {
                    'request_id': request_id,
                    'server_url': DYNAMODB_MCP_CONFIG['server_url'],
                    'available': DYNAMODB_MCP_CONFIG['available']
                },
                'ERROR'
            )
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "DynamoDB MCP server not available - connection failed during container startup",
                    "request_id": request_id
                })
            }
        
        logger.info(f"✅ DynamoDB MCP server available: {DYNAMODB_MCP_CONFIG['server_url']}")
        
        # Parse the request - handle both direct event and body-wrapped formats
        logger.info(f"📊 Parsing request...")
        
        try:
            # Check if operation is directly in the event (Lambda invocation format)
            if 'operation' in event:
                logger.info(f"✅ Found 'operation' directly in event")
                body = event
            # Check if operation is in the body field (API Gateway format)
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
                'dynamodb-mcp-handler',
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
        operation = body.get('operation', 'status')
        table_name = body.get('table_name', '')
        
        logger.info(f"📊 Operation: {operation}")
        logger.info(f"📊 Table name: {table_name}")
        
        # Validate required parameters
        if operation in ['read', 'write', 'update', 'delete', 'query', 'scan'] and not table_name:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error("❌ Table name is required for this operation")
            log_custom_error(
                'dynamodb-mcp-handler',
                'Table name is required for this operation',
                {
                    'request_id': request_id,
                    'operation': operation,
                    'processing_time': processing_time
                },
                'WARNING'
            )
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": "Table name is required for this operation",
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Route to appropriate MCP operation
        if operation == 'read':
            logger.info(f"📖 Processing read operation")
            key = body.get('key', {})
            
            if not key:
                processing_time = (datetime.now() - start_time).total_seconds()
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "Key is required for read operation",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            result = call_dynamodb_mcp_server("get_item", {
                "table_name": table_name,
                "key": key
            })
            
        elif operation == 'write':
            logger.info(f"✍️ Processing write operation")
            item = body.get('item', {})
            
            if not item:
                processing_time = (datetime.now() - start_time).total_seconds()
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "Item is required for write operation",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            result = call_dynamodb_mcp_server("put_item", {
                "table_name": table_name,
                "item": item
            })
            
        elif operation == 'update':
            logger.info(f"🔄 Processing update operation")
            key = body.get('key', {})
            update_expression = body.get('update_expression', '')
            expression_attribute_names = body.get('expression_attribute_names', {})
            expression_attribute_values = body.get('expression_attribute_values', {})
            
            if not key or not update_expression:
                processing_time = (datetime.now() - start_time).total_seconds()
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "Key and update_expression are required for update operation",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            result = call_dynamodb_mcp_server("update_item", {
                "table_name": table_name,
                "key": key,
                "update_expression": update_expression,
                "expression_attribute_names": expression_attribute_names,
                "expression_attribute_values": expression_attribute_values
            })
            
        elif operation == 'delete':
            logger.info(f"🗑️ Processing delete operation")
            key = body.get('key', {})
            
            if not key:
                processing_time = (datetime.now() - start_time).total_seconds()
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "Key is required for delete operation",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            result = call_dynamodb_mcp_server("delete_item", {
                "table_name": table_name,
                "key": key
            })
            
        elif operation == 'query':
            logger.info(f"🔍 Processing query operation")
            key_condition_expression = body.get('key_condition_expression', '')
            filter_expression = body.get('filter_expression', '')
            expression_attribute_names = body.get('expression_attribute_names', {})
            expression_attribute_values = body.get('expression_attribute_values', {})
            limit = body.get('limit')
            
            if not key_condition_expression:
                processing_time = (datetime.now() - start_time).total_seconds()
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "key_condition_expression is required for query operation",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            query_params = {
                "table_name": table_name,
                "key_condition_expression": key_condition_expression
            }
            
            if filter_expression:
                query_params["filter_expression"] = filter_expression
            if expression_attribute_names:
                query_params["expression_attribute_names"] = expression_attribute_names
            if expression_attribute_values:
                query_params["expression_attribute_values"] = expression_attribute_values
            if limit:
                query_params["limit"] = limit
            
            result = call_dynamodb_mcp_server("query_table", query_params)
            
        elif operation == 'scan':
            logger.info(f"🔍 Processing scan operation")
            filter_expression = body.get('filter_expression', '')
            expression_attribute_names = body.get('expression_attribute_names', {})
            expression_attribute_values = body.get('expression_attribute_values', {})
            limit = body.get('limit')
            
            scan_params = {
                "table_name": table_name
            }
            
            if filter_expression:
                scan_params["filter_expression"] = filter_expression
            if expression_attribute_names:
                scan_params["expression_attribute_names"] = expression_attribute_names
            if expression_attribute_values:
                scan_params["expression_attribute_values"] = expression_attribute_values
            if limit:
                scan_params["limit"] = limit
            
            result = call_dynamodb_mcp_server("scan_table", scan_params)
            
        elif operation == 'list_tables':
            logger.info(f"📋 Processing list tables operation")
            result = call_dynamodb_mcp_server("list_tables", {})
            
        elif operation == 'describe_table':
            logger.info(f"📄 Processing describe table operation")
            result = call_dynamodb_mcp_server("describe_table", {
                "table_name": table_name
            })
            
        else:
            # Return MCP server status
            logger.info(f"📊 No specific operation found, returning MCP server status")
            processing_time = (datetime.now() - start_time).total_seconds()
            status_info = {
                "success": True,
                "message": "DynamoDB MCP server is ready",
                "server_url": DYNAMODB_MCP_CONFIG["server_url"],
                "available": DYNAMODB_MCP_CONFIG["available"],
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Status response: {status_info}")
            return {
                "statusCode": 200,
                "body": json.dumps(status_info)
            }
        
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
        
    except json.JSONDecodeError as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ JSON decode error in DynamoDB MCP handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'dynamodb-mcp-handler',
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
        logger.error(f"❌ Error in DynamoDB MCP server handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'dynamodb-mcp-handler',
            e,
            context,
            {
                'request_id': request_id,
                'operation': event.get('operation', 'unknown'),
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
