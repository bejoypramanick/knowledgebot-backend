#!/usr/bin/env python3
"""
DynamoDB CRUD - Single Purpose Lambda
Performs CRUD operations on DynamoDB
"""

import json
import os
import traceback
import sys
from typing import Dict, Any, List
from datetime import datetime
import boto3
import logging

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

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Perform DynamoDB CRUD operations with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== DYNAMODB CRUD STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Parse request body with validation
        try:
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
                logger.info("✅ Successfully parsed JSON body")
            else:
                body = event.get('body', {})
                logger.info("✅ Using direct body object")
            
            logger.info(f"📊 Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'Not a dict'}")
            
        except json.JSONDecodeError as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ JSON decode error in DynamoDB CRUD: {e}")
            logger.error(f"📊 Stack trace: {traceback.format_exc()}")
            
            log_error(
                'dynamodb-crud-handler',
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
                    "request_id": request_id,
                    "processing_time": processing_time,
                    "timestamp": datetime.now().isoformat()
                })
            }
        
        # Extract and validate parameters
        operation = body.get('operation', '')  # read, write, update, delete, batch_read
        table_name = body.get('table_name', '')
        
        logger.info(f"📊 Operation: {operation}")
        logger.info(f"📊 Table name: {table_name}")
        
        # Validate required parameters
        if not operation or not table_name:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = "Operation and table_name are required"
            logger.error(f"❌ Validation error: {error_msg}")
            
            log_error(
                'dynamodb-crud-handler',
                ValueError(error_msg),
                context,
                {
                    'request_id': request_id,
                    'operation': operation,
                    'table_name': table_name,
                    'processing_time': processing_time,
                    'error_type': 'ValidationError'
                },
                'WARNING'
            )
            
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
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Validate operation type
        valid_operations = ['read', 'write', 'update', 'delete', 'batch_read']
        if operation not in valid_operations:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Unsupported operation: {operation}. Valid operations: {valid_operations}"
            logger.error(f"❌ Validation error: {error_msg}")
            
            log_error(
                'dynamodb-crud-handler',
                ValueError(error_msg),
                context,
                {
                    'request_id': request_id,
                    'operation': operation,
                    'table_name': table_name,
                    'processing_time': processing_time,
                    'error_type': 'ValidationError'
                },
                'WARNING'
            )
            
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
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Initialize DynamoDB table
        try:
            table = dynamodb.Table(table_name)
            logger.info(f"✅ DynamoDB table '{table_name}' initialized successfully")
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Failed to initialize DynamoDB table '{table_name}': {str(e)}"
            logger.error(f"❌ DynamoDB table initialization error: {error_msg}")
            
            log_error(
                'dynamodb-crud-handler',
                e,
                context,
                {
                    'request_id': request_id,
                    'operation': operation,
                    'table_name': table_name,
                    'processing_time': processing_time,
                    'error_type': 'DynamoDBError'
                },
                'ERROR'
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
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Execute operation based on type
        if operation == 'read':
            logger.info("🔍 Processing read operation")
            key = body.get('key', {})
            
            if not key:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = "Key is required for read operation"
                logger.error(f"❌ Validation error: {error_msg}")
                
                log_error(
                    'dynamodb-crud-handler',
                    ValueError(error_msg),
                    context,
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                
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
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            try:
                logger.info(f"📊 Reading item with key: {key}")
                response = table.get_item(Key=key)
                item = response.get('Item')
                
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Read operation completed successfully")
                logger.info(f"📊 Processing time: {processing_time:.3f}s")
                logger.info(f"📊 Item found: {item is not None}")
                
                # Log success to centralized error logger
                log_custom_error(
                    'dynamodb-crud-handler',
                    'read_operation_success',
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'item_found': item is not None,
                        'processing_time': processing_time
                    },
                    'INFO'
                )
                
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Credentials": "true"
                    },
                    "body": json.dumps({
                        "success": True,
                        "operation": "read",
                        "item": item,
                        "found": item is not None,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
                
            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = f"Failed to read item from DynamoDB: {str(e)}"
                logger.error(f"❌ DynamoDB read error: {error_msg}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                
                log_error(
                    'dynamodb-crud-handler',
                    e,
                    context,
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'key': key,
                        'processing_time': processing_time,
                        'error_type': 'DynamoDBReadError'
                    },
                    'ERROR'
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
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
        
        elif operation == 'write':
            logger.info("📝 Processing write operation")
            item = body.get('item', {})
            
            if not item:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = "Item is required for write operation"
                logger.error(f"❌ Validation error: {error_msg}")
                
                log_error(
                    'dynamodb-crud-handler',
                    ValueError(error_msg),
                    context,
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                
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
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            try:
                logger.info(f"📊 Writing item: {json.dumps(item, default=str)[:200]}{'...' if len(json.dumps(item, default=str)) > 200 else ''}")
                table.put_item(Item=item)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Write operation completed successfully")
                logger.info(f"📊 Processing time: {processing_time:.3f}s")
                logger.info(f"📊 Item ID: {item.get('id', 'unknown')}")
                
                # Log success to centralized error logger
                log_custom_error(
                    'dynamodb-crud-handler',
                    'write_operation_success',
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'item_id': item.get('id', 'unknown'),
                        'processing_time': processing_time
                    },
                    'INFO'
                )
                
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Credentials": "true"
                    },
                    "body": json.dumps({
                        "success": True,
                        "operation": "write",
                        "item_id": item.get('id', 'unknown'),
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
                
            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = f"Failed to write item to DynamoDB: {str(e)}"
                logger.error(f"❌ DynamoDB write error: {error_msg}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                
                log_error(
                    'dynamodb-crud-handler',
                    e,
                    context,
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'item_id': item.get('id', 'unknown'),
                        'processing_time': processing_time,
                        'error_type': 'DynamoDBWriteError'
                    },
                    'ERROR'
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
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
        
        elif operation == 'batch_read':
            logger.info("📚 Processing batch read operation")
            keys = body.get('keys', [])
            
            if not keys:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = "Keys are required for batch_read operation"
                logger.error(f"❌ Validation error: {error_msg}")
                
                log_error(
                    'dynamodb-crud-handler',
                    ValueError(error_msg),
                    context,
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                
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
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            try:
                logger.info(f"📊 Batch reading {len(keys)} items")
                response = dynamodb.batch_get_item(
                    RequestItems={
                        table_name: {
                            'Keys': keys
                        }
                    }
                )
                
                items = response.get('Responses', {}).get(table_name, [])
                
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Batch read operation completed successfully")
                logger.info(f"📊 Processing time: {processing_time:.3f}s")
                logger.info(f"📊 Items found: {len(items)}")
                
                # Log success to centralized error logger
                log_custom_error(
                    'dynamodb-crud-handler',
                    'batch_read_operation_success',
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'keys_requested': len(keys),
                        'items_found': len(items),
                        'processing_time': processing_time
                    },
                    'INFO'
                )
                
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Credentials": "true"
                    },
                    "body": json.dumps({
                        "success": True,
                        "operation": "batch_read",
                        "items": items,
                        "total_items": len(items),
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
                
            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = f"Failed to batch read items from DynamoDB: {str(e)}"
                logger.error(f"❌ DynamoDB batch read error: {error_msg}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                
                log_error(
                    'dynamodb-crud-handler',
                    e,
                    context,
                    {
                        'request_id': request_id,
                        'operation': operation,
                        'table_name': table_name,
                        'keys_count': len(keys),
                        'processing_time': processing_time,
                        'error_type': 'DynamoDBBatchReadError'
                    },
                    'ERROR'
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
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
        
        else:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Unsupported operation: {operation}"
            logger.error(f"❌ Validation error: {error_msg}")
            
            log_error(
                'dynamodb-crud-handler',
                ValueError(error_msg),
                context,
                {
                    'request_id': request_id,
                    'operation': operation,
                    'table_name': table_name,
                    'processing_time': processing_time,
                    'error_type': 'ValidationError'
                },
                'WARNING'
            )
            
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
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ CRITICAL ERROR in DynamoDB CRUD: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Full stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'dynamodb-crud-handler',
            e,
            context,
            {
                'request_id': request_id,
                'operation_type': event.get('operation_type', 'unknown'),
                'event_keys': list(event.keys()) if event else [],
                'processing_time': processing_time,
                'error_type': 'HandlerError'
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
                "error_type": type(e).__name__,
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            })
        }
