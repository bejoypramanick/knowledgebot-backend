#!/usr/bin/env python3
"""
DynamoDB CRUD - Single Purpose Lambda
Performs CRUD operations on DynamoDB
"""

import json
import os
from typing import Dict, Any, List
import boto3
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Perform DynamoDB CRUD operations"""
    logger.info("=== DYNAMODB CRUD STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        operation = body.get('operation', '')  # read, write, update, delete, batch_read
        table_name = body.get('table_name', '')
        
        if not operation or not table_name:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Operation and table_name are required"})
            }
        
        table = dynamodb.Table(table_name)
        
        if operation == 'read':
            key = body.get('key', {})
            if not key:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Key is required for read operation"})
                }
            
            response = table.get_item(Key=key)
            item = response.get('Item')
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": True,
                    "operation": "read",
                    "item": item,
                    "found": item is not None
                })
            }
        
        elif operation == 'write':
            item = body.get('item', {})
            if not item:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Item is required for write operation"})
                }
            
            table.put_item(Item=item)
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": True,
                    "operation": "write",
                    "item_id": item.get('id', 'unknown')
                })
            }
        
        elif operation == 'batch_read':
            keys = body.get('keys', [])
            if not keys:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Keys are required for batch_read operation"})
                }
            
            response = dynamodb.batch_get_item(
                RequestItems={
                    table_name: {
                        'Keys': keys
                    }
                }
            )
            
            items = response.get('Responses', {}).get(table_name, [])
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": True,
                    "operation": "batch_read",
                    "items": items,
                    "total_items": len(items)
                })
            }
        
        else:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Unsupported operation: {operation}"})
            }
        
    except Exception as e:
        logger.error(f"Error in DynamoDB CRUD: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
