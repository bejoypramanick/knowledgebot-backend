#!/usr/bin/env python3
"""
DynamoDB MCP Client - Communicates with official DynamoDB MCP server
Handles JSON-RPC calls to the DynamoDB MCP server running via official Docker image
"""

import json
import logging
import os
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamoDBMCPClient:
    """Client for communicating with DynamoDB MCP server via JSON-RPC"""
    
    def __init__(self, dynamodb_mcp_url: str = None):
        self.dynamodb_mcp_url = dynamodb_mcp_url or os.environ.get(
            'DYNAMODB_MCP_URL', 
            'http://localhost:3000/mcp'
        )
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_jsonrpc_call(self, method: str, params: Dict[str, Any] = None, request_id: int = 1) -> Dict[str, Any]:
        """Make a JSON-RPC call to the DynamoDB MCP server"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {}
            }
            
            logger.info(f"Making JSON-RPC call to {self.dynamodb_mcp_url}: {method}")
            
            async with self.session.post(
                self.dynamodb_mcp_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"JSON-RPC call successful: {method}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"JSON-RPC call failed: {response.status} - {error_text}")
                    return {
                        "error": {
                            "code": response.status,
                            "message": f"HTTP {response.status}: {error_text}"
                        }
                    }
        
        except Exception as e:
            logger.error(f"Error making JSON-RPC call: {e}")
            return {
                "error": {
                    "code": -1,
                    "message": str(e)
                }
            }
    
    async def list_tables(self, limit: int = 10) -> Dict[str, Any]:
        """List all DynamoDB tables"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "list-tables",
            "arguments": {
                "limit": limit
            }
        })
    
    async def create_table(self, table_name: str, partition_key: str, partition_key_type: str = "S", 
                          sort_key: str = None, sort_key_type: str = "S", 
                          read_capacity: int = 5, write_capacity: int = 5) -> Dict[str, Any]:
        """Create a new DynamoDB table"""
        args = {
            "tableName": table_name,
            "partitionKey": partition_key,
            "partitionKeyType": partition_key_type,
            "readCapacity": read_capacity,
            "writeCapacity": write_capacity
        }
        
        if sort_key:
            args["sortKey"] = sort_key
            args["sortKeyType"] = sort_key_type
        
        return await self._make_jsonrpc_call("tools/call", {
            "name": "create-table",
            "arguments": args
        })
    
    async def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Describe a specific DynamoDB table"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "describe-table",
            "arguments": {
                "tableName": table_name
            }
        })
    
    async def put_item(self, table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Put (insert/update) an item in a DynamoDB table"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "put-item",
            "arguments": {
                "tableName": table_name,
                "item": item
            }
        })
    
    async def get_item(self, table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
        """Get (read) an item from a DynamoDB table"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "get-item",
            "arguments": {
                "tableName": table_name,
                "key": key
            }
        })
    
    async def update_item(self, table_name: str, key: Dict[str, Any], 
                         update_expression: str, expression_attribute_values: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update an item in a DynamoDB table"""
        args = {
            "tableName": table_name,
            "key": key,
            "updateExpression": update_expression
        }
        
        if expression_attribute_values:
            args["expressionAttributeValues"] = expression_attribute_values
        
        return await self._make_jsonrpc_call("tools/call", {
            "name": "update-item",
            "arguments": args
        })
    
    async def delete_item(self, table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an item from a DynamoDB table"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "delete-item",
            "arguments": {
                "tableName": table_name,
                "key": key
            }
        })
    
    async def scan(self, table_name: str, filter_expression: str = None, 
                   expression_attribute_values: Dict[str, Any] = None, 
                   limit: int = None) -> Dict[str, Any]:
        """Scan a DynamoDB table"""
        args = {
            "tableName": table_name
        }
        
        if filter_expression:
            args["filterExpression"] = filter_expression
        if expression_attribute_values:
            args["expressionAttributeValues"] = expression_attribute_values
        if limit:
            args["limit"] = limit
        
        return await self._make_jsonrpc_call("tools/call", {
            "name": "scan",
            "arguments": args
        })
    
    async def query(self, table_name: str, key_condition_expression: str,
                    expression_attribute_values: Dict[str, Any] = None,
                    filter_expression: str = None, limit: int = None) -> Dict[str, Any]:
        """Query a DynamoDB table"""
        args = {
            "tableName": table_name,
            "keyConditionExpression": key_condition_expression
        }
        
        if expression_attribute_values:
            args["expressionAttributeValues"] = expression_attribute_values
        if filter_expression:
            args["filterExpression"] = filter_expression
        if limit:
            args["limit"] = limit
        
        return await self._make_jsonrpc_call("tools/call", {
            "name": "query",
            "arguments": args
        })
    
    async def get_health(self) -> Dict[str, Any]:
        """Check DynamoDB MCP server health"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "get_health",
            "arguments": {}
        })

# Example usage and testing
async def test_dynamodb_mcp_client():
    """Test the DynamoDB MCP client"""
    async with DynamoDBMCPClient() as client:
        # Test health check
        health = await client.get_health()
        print("Health check:", json.dumps(health, indent=2))
        
        # Test list tables
        tables = await client.list_tables()
        print("Tables:", json.dumps(tables, indent=2))

if __name__ == "__main__":
    asyncio.run(test_dynamodb_mcp_client())
