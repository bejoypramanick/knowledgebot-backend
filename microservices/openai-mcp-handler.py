#!/usr/bin/env python3
"""
OpenAI MCP Handler Lambda
Handles OpenAI operations via MCP server with comprehensive logging and error handling
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
OPENAI_MCP_CONFIG = {
    "server_url": os.environ.get('OPENAI_MCP_SERVER_URL', ''),
    "timeout": int(os.environ.get('OPENAI_MCP_SERVER_TIMEOUT', '30')),
    "available": False
}

def check_mcp_server_availability():
    """Check if OpenAI MCP server is available"""
    try:
        if not OPENAI_MCP_CONFIG["server_url"]:
            logger.warning("⚠️ OpenAI MCP server URL not configured")
            return False
        
        # Try to get health status
        response = requests.get(
            f"{OPENAI_MCP_CONFIG['server_url']}/health",
            timeout=5
        )
        
        if response.status_code == 200:
            OPENAI_MCP_CONFIG["available"] = True
            logger.info(f"✅ OpenAI MCP server is available: {OPENAI_MCP_CONFIG['server_url']}")
            return True
        else:
            logger.warning(f"⚠️ OpenAI MCP server returned status {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ OpenAI MCP server not available: {e}")
        OPENAI_MCP_CONFIG["available"] = False
        return False

def call_openai_mcp_server(operation_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call OpenAI MCP server for operations"""
    try:
        logger.info(f"🤖 Calling OpenAI MCP server for {operation_type}")
        
        if not OPENAI_MCP_CONFIG["available"]:
            logger.error("❌ OpenAI MCP server not available")
            return {
                "success": False,
                "error": "OpenAI MCP server not available"
            }
        
        # Prepare MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": operation_type,
                "arguments": payload
            }
        }
        
        # Make request to MCP server
        response = requests.post(
            OPENAI_MCP_CONFIG["server_url"],
            json=mcp_request,
            timeout=OPENAI_MCP_CONFIG["timeout"],
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
                        logger.info(f"✅ OpenAI MCP server {operation_type} completed successfully")
                        return parsed_response
                    except json.JSONDecodeError:
                        logger.error(f"❌ Invalid JSON response from OpenAI MCP server: {response_text}")
                        return {
                            "success": False,
                            "error": "Invalid response format from OpenAI MCP server"
                        }
                else:
                    logger.error(f"❌ Empty response from OpenAI MCP server")
                    return {
                        "success": False,
                        "error": "Empty response from OpenAI MCP server"
                    }
            else:
                logger.error(f"❌ Error in OpenAI MCP server response: {result}")
                return {
                    "success": False,
                    "error": f"OpenAI MCP server error: {result.get('error', 'Unknown error')}"
                }
        else:
            logger.error(f"❌ OpenAI MCP server returned status {response.status_code}: {response.text}")
            return {
                "success": False,
                "error": f"OpenAI MCP server returned status {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"⏰ OpenAI MCP server timeout after {OPENAI_MCP_CONFIG['timeout']}s")
        return {
            "success": False,
            "error": f"OpenAI MCP server timeout after {OPENAI_MCP_CONFIG['timeout']}s"
        }
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Connection error to OpenAI MCP server")
        return {
            "success": False,
            "error": "Connection error to OpenAI MCP server"
        }
    except Exception as e:
        logger.error(f"❌ Error calling OpenAI MCP server: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """OpenAI MCP Handler - Performs OpenAI operations via MCP server with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== OPENAI MCP HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Check MCP server availability
        check_mcp_server_availability()
        
        if not OPENAI_MCP_CONFIG["available"]:
            logger.error("❌ OpenAI MCP server not available - connection failed")
            log_service_failure(
                'openai-mcp-handler',
                'MCP server not available',
                {
                    'request_id': request_id,
                    'server_url': OPENAI_MCP_CONFIG['server_url'],
                    'available': OPENAI_MCP_CONFIG['available']
                },
                'ERROR'
            )
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "OpenAI MCP server not available - connection failed during container startup",
                    "request_id": request_id
                })
            }
        
        logger.info(f"✅ OpenAI MCP server available: {OPENAI_MCP_CONFIG['server_url']}")
        
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
                'openai-mcp-handler',
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
        
        if operation_type == 'chat':
            logger.info(f"💬 Processing chat completion request via MCP server")
            messages = body.get('messages', [])
            model = body.get('model', 'gpt-4o-mini')
            max_tokens = body.get('max_tokens', 1000)
            temperature = body.get('temperature', 0.7)
            
            logger.info(f"📝 Messages count: {len(messages)}")
            logger.info(f"📝 Model: {model}")
            logger.info(f"📝 Max tokens: {max_tokens}")
            logger.info(f"📝 Temperature: {temperature}")
            
            # Validate input
            if not messages:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error("❌ No messages provided for chat completion")
                log_custom_error(
                    'openai-mcp-handler',
                    'No messages provided for chat completion',
                    {
                        'request_id': request_id,
                        'processing_time': processing_time
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "No messages provided for chat completion",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            # Call OpenAI MCP server
            mcp_payload = {
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            result = call_openai_mcp_server("chat_completion", mcp_payload)
            
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
            
        elif operation_type == 'completion':
            logger.info(f"📝 Processing text completion request via MCP server")
            prompt = body.get('prompt', '')
            model = body.get('model', 'gpt-3.5-turbo-instruct')
            max_tokens = body.get('max_tokens', 1000)
            temperature = body.get('temperature', 0.7)
            
            logger.info(f"📝 Prompt length: {len(prompt)}")
            logger.info(f"📝 Model: {model}")
            logger.info(f"📝 Max tokens: {max_tokens}")
            logger.info(f"📝 Temperature: {temperature}")
            
            # Validate input
            if not prompt:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error("❌ No prompt provided for completion")
                log_custom_error(
                    'openai-mcp-handler',
                    'No prompt provided for completion',
                    {
                        'request_id': request_id,
                        'processing_time': processing_time
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "No prompt provided for completion",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            # Call OpenAI MCP server
            mcp_payload = {
                "prompt": prompt,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            result = call_openai_mcp_server("completion", mcp_payload)
            
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
            
        elif operation_type == 'embedding':
            logger.info(f"🧠 Processing embedding generation request via MCP server")
            input_texts = body.get('input', [])
            model = body.get('model', 'text-embedding-3-small')
            
            logger.info(f"📝 Input texts count: {len(input_texts) if isinstance(input_texts, list) else 1}")
            logger.info(f"📝 Model: {model}")
            
            # Validate input
            if not input_texts:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error("❌ No input provided for embedding")
                log_custom_error(
                    'openai-mcp-handler',
                    'No input provided for embedding',
                    {
                        'request_id': request_id,
                        'processing_time': processing_time
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "No input provided for embedding",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            # Call OpenAI MCP server
            mcp_payload = {
                "input": input_texts,
                "model": model
            }
            
            result = call_openai_mcp_server("embedding", mcp_payload)
            
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
                "message": "OpenAI MCP server is ready",
                "server_url": OPENAI_MCP_CONFIG["server_url"],
                "available": OPENAI_MCP_CONFIG["available"],
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
        logger.error(f"❌ JSON decode error in OpenAI MCP handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'openai-mcp-handler',
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
        logger.error(f"❌ Error in OpenAI MCP server handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'openai-mcp-handler',
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
