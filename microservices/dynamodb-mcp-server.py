#!/usr/bin/env python3
"""
DynamoDB MCP Server - Based on awslabs/mcp dynamodb-mcp-server
Provides DynamoDB operations through MCP protocol
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# AWS DynamoDB imports
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamoDBMCPServer:
    """DynamoDB MCP Server for database operations"""
    
    def __init__(self):
        self.server = Server("dynamodb-mcp-server")
        self.dynamodb = None
        self._setup_handlers()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize DynamoDB client"""
        try:
            region_name = os.environ.get('AWS_REGION', 'us-east-1')
            
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=region_name
            )
            
            # Test connection by listing tables
            list(self.dynamodb.tables.all())
            
            logger.info(f"✅ DynamoDB client initialized successfully in region: {region_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize DynamoDB client: {e}")
            self.dynamodb = None
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="get_item",
                    description="Get an item from a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            },
                            "key": {
                                "type": "object",
                                "description": "Primary key of the item to retrieve"
                            }
                        },
                        "required": ["table_name", "key"]
                    }
                ),
                Tool(
                    name="put_item",
                    description="Put an item into a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            },
                            "item": {
                                "type": "object",
                                "description": "Item to put into the table"
                            }
                        },
                        "required": ["table_name", "item"]
                    }
                ),
                Tool(
                    name="update_item",
                    description="Update an item in a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            },
                            "key": {
                                "type": "object",
                                "description": "Primary key of the item to update"
                            },
                            "update_expression": {
                                "type": "string",
                                "description": "Update expression (e.g., 'SET #attr = :val')"
                            },
                            "expression_attribute_names": {
                                "type": "object",
                                "description": "Expression attribute names"
                            },
                            "expression_attribute_values": {
                                "type": "object",
                                "description": "Expression attribute values"
                            }
                        },
                        "required": ["table_name", "key", "update_expression"]
                    }
                ),
                Tool(
                    name="delete_item",
                    description="Delete an item from a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            },
                            "key": {
                                "type": "object",
                                "description": "Primary key of the item to delete"
                            }
                        },
                        "required": ["table_name", "key"]
                    }
                ),
                Tool(
                    name="query_table",
                    description="Query items from a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            },
                            "key_condition_expression": {
                                "type": "string",
                                "description": "Key condition expression"
                            },
                            "filter_expression": {
                                "type": "string",
                                "description": "Filter expression"
                            },
                            "expression_attribute_names": {
                                "type": "object",
                                "description": "Expression attribute names"
                            },
                            "expression_attribute_values": {
                                "type": "object",
                                "description": "Expression attribute values"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of items to return"
                            }
                        },
                        "required": ["table_name", "key_condition_expression"]
                    }
                ),
                Tool(
                    name="scan_table",
                    description="Scan items from a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            },
                            "filter_expression": {
                                "type": "string",
                                "description": "Filter expression"
                            },
                            "expression_attribute_names": {
                                "type": "object",
                                "description": "Expression attribute names"
                            },
                            "expression_attribute_values": {
                                "type": "object",
                                "description": "Expression attribute values"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of items to return"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="list_tables",
                    description="List all DynamoDB tables",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="describe_table",
                    description="Describe a DynamoDB table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the DynamoDB table"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="get_health",
                    description="Check server health status",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "get_item":
                    return await self._get_item(arguments)
                elif name == "put_item":
                    return await self._put_item(arguments)
                elif name == "update_item":
                    return await self._update_item(arguments)
                elif name == "delete_item":
                    return await self._delete_item(arguments)
                elif name == "query_table":
                    return await self._query_table(arguments)
                elif name == "scan_table":
                    return await self._scan_table(arguments)
                elif name == "list_tables":
                    return await self._list_tables()
                elif name == "describe_table":
                    return await self._describe_table(arguments)
                elif name == "get_health":
                    return await self._get_health()
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def _get_item(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get item from DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            key = arguments.get("key")
            
            if not table_name or not key:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name and key are required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key=key)
            
            result_data = {
                "success": True,
                "item": response.get("Item"),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error getting item: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _put_item(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Put item into DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            item = arguments.get("item")
            
            if not table_name or not item:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name and item are required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            response = table.put_item(Item=item)
            
            result_data = {
                "success": True,
                "response_metadata": response.get("ResponseMetadata"),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error putting item: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _update_item(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Update item in DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            key = arguments.get("key")
            update_expression = arguments.get("update_expression")
            expression_attribute_names = arguments.get("expression_attribute_names", {})
            expression_attribute_values = arguments.get("expression_attribute_values", {})
            
            if not table_name or not key or not update_expression:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name, key, and update_expression are required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            
            update_kwargs = {
                "Key": key,
                "UpdateExpression": update_expression
            }
            
            if expression_attribute_names:
                update_kwargs["ExpressionAttributeNames"] = expression_attribute_names
            if expression_attribute_values:
                update_kwargs["ExpressionAttributeValues"] = expression_attribute_values
            
            response = table.update_item(**update_kwargs)
            
            result_data = {
                "success": True,
                "response_metadata": response.get("ResponseMetadata"),
                "attributes": response.get("Attributes"),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error updating item: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _delete_item(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Delete item from DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            key = arguments.get("key")
            
            if not table_name or not key:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name and key are required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            response = table.delete_item(Key=key)
            
            result_data = {
                "success": True,
                "response_metadata": response.get("ResponseMetadata"),
                "attributes": response.get("Attributes"),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error deleting item: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _query_table(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Query items from DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            key_condition_expression = arguments.get("key_condition_expression")
            filter_expression = arguments.get("filter_expression")
            expression_attribute_names = arguments.get("expression_attribute_names", {})
            expression_attribute_values = arguments.get("expression_attribute_values", {})
            limit = arguments.get("limit")
            
            if not table_name or not key_condition_expression:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name and key_condition_expression are required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            
            query_kwargs = {
                "KeyConditionExpression": key_condition_expression
            }
            
            if filter_expression:
                query_kwargs["FilterExpression"] = filter_expression
            if expression_attribute_names:
                query_kwargs["ExpressionAttributeNames"] = expression_attribute_names
            if expression_attribute_values:
                query_kwargs["ExpressionAttributeValues"] = expression_attribute_values
            if limit:
                query_kwargs["Limit"] = limit
            
            response = table.query(**query_kwargs)
            
            result_data = {
                "success": True,
                "items": response.get("Items", []),
                "count": response.get("Count", 0),
                "scanned_count": response.get("ScannedCount", 0),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error querying table: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _scan_table(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Scan items from DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            filter_expression = arguments.get("filter_expression")
            expression_attribute_names = arguments.get("expression_attribute_names", {})
            expression_attribute_values = arguments.get("expression_attribute_values", {})
            limit = arguments.get("limit")
            
            if not table_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name is required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            
            scan_kwargs = {}
            
            if filter_expression:
                scan_kwargs["FilterExpression"] = filter_expression
            if expression_attribute_names:
                scan_kwargs["ExpressionAttributeNames"] = expression_attribute_names
            if expression_attribute_values:
                scan_kwargs["ExpressionAttributeValues"] = expression_attribute_values
            if limit:
                scan_kwargs["Limit"] = limit
            
            response = table.scan(**scan_kwargs)
            
            result_data = {
                "success": True,
                "items": response.get("Items", []),
                "count": response.get("Count", 0),
                "scanned_count": response.get("ScannedCount", 0),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error scanning table: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _list_tables(self) -> List[TextContent]:
        """List all DynamoDB tables"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            client = boto3.client('dynamodb')
            response = client.list_tables()
            
            result_data = {
                "success": True,
                "tables": response.get("TableNames", [])
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _describe_table(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Describe a DynamoDB table"""
        try:
            if not self.dynamodb:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "DynamoDB client not initialized"
                    })
                )]
            
            table_name = arguments.get("table_name")
            
            if not table_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "table_name is required"
                    })
                )]
            
            table = self.dynamodb.Table(table_name)
            response = table.describe_table()
            
            result_data = {
                "success": True,
                "table": response.get("Table", {}),
                "table_name": table_name
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2, default=str)
            )]
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"DynamoDB error: {e.response['Error']['Message']}"
                }, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error describing table: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _get_health(self) -> List[TextContent]:
        """Get server health status"""
        status = {
            "status": "healthy" if self.dynamodb else "unhealthy",
            "client_initialized": self.dynamodb is not None,
            "server": "dynamodb-mcp-server",
            "version": "1.0.0"
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(status, indent=2)
        )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="dynamodb-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """Main entry point"""
    server = DynamoDBMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
