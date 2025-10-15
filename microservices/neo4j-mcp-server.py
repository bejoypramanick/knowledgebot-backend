#!/usr/bin/env python3
"""
Neo4j MCP Server - Based on neo4j-contrib/mcp-neo4j
Provides Neo4j database operations through MCP protocol
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

# Neo4j imports
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jMCPServer:
    """Neo4j MCP Server for database operations"""
    
    def __init__(self):
        self.server = Server("neo4j-mcp-server")
        self.driver = None
        self._setup_handlers()
        self._initialize_driver()
    
    def _initialize_driver(self):
        """Initialize Neo4j driver"""
        try:
            neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
            neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
            neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')
            
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            logger.info("✅ Neo4j driver initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Neo4j driver: {e}")
            self.driver = None
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="execute_cypher",
                    description="Execute a Cypher query against the Neo4j database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Cypher query to execute"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Query parameters",
                                "default": {}
                            },
                            "operation_type": {
                                "type": "string",
                                "enum": ["read", "write"],
                                "description": "Type of operation (read or write)",
                                "default": "read"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_schema",
                    description="Get the database schema (labels, relationship types, property keys)",
                    inputSchema={
                        "type": "object",
                        "properties": {}
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
                if name == "execute_cypher":
                    return await self._execute_cypher(arguments)
                elif name == "get_schema":
                    return await self._get_schema()
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
    
    async def _execute_cypher(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute Cypher query"""
        try:
            if not self.driver:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Neo4j driver not initialized"
                    })
                )]
            
            query = arguments.get("query")
            parameters = arguments.get("parameters", {})
            operation_type = arguments.get("operation_type", "read")
            
            if not query:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Query is required"
                    })
                )]
            
            with self.driver.session() as session:
                result = session.run(query, parameters)
                
                # Collect results
                records = []
                for record in result:
                    records.append(dict(record))
                
                # Get query statistics
                summary = result.consume()
                stats = {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added,
                    "labels_removed": summary.counters.labels_removed,
                    "indexes_added": summary.counters.indexes_added,
                    "indexes_removed": summary.counters.indexes_removed,
                    "constraints_added": summary.counters.constraints_added,
                    "constraints_removed": summary.counters.constraints_removed
                }
                
                result_data = {
                    "success": True,
                    "data": records,
                    "summary": {
                        "operation_type": operation_type,
                        "records_count": len(records),
                        "stats": stats
                    }
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result_data, indent=2)
                )]
                
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _get_schema(self) -> List[TextContent]:
        """Get database schema"""
        try:
            if not self.driver:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Neo4j driver not initialized"
                    })
                )]
            
            with self.driver.session() as session:
                # Get labels
                labels_result = session.run("CALL db.labels()")
                labels = [record["label"] for record in labels_result]
                
                # Get relationship types
                rel_types_result = session.run("CALL db.relationshipTypes()")
                relationship_types = [record["relationshipType"] for record in rel_types_result]
                
                # Get property keys
                prop_keys_result = session.run("CALL db.propertyKeys()")
                property_keys = [record["propertyKey"] for record in prop_keys_result]
                
                schema = {
                    "success": True,
                    "schema": {
                        "labels": labels,
                        "relationship_types": relationship_types,
                        "property_keys": property_keys
                    }
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(schema, indent=2)
                )]
                
        except Exception as e:
            logger.error(f"Error getting schema: {e}")
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
            "status": "healthy" if self.driver else "unhealthy",
            "driver_initialized": self.driver is not None,
            "server": "neo4j-mcp-server",
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
                    server_name="neo4j-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )
    
    async def process_mcp_request(self, request_data):
        """Process MCP request for Lambda handler"""
        try:
            # Handle different types of MCP requests
            if isinstance(request_data, dict):
                method = request_data.get('method', '')
                params = request_data.get('params', {})
                
                if method == 'tools/call':
                    tool_name = params.get('name', '')
                    arguments = params.get('arguments', {})
                    
                    if tool_name == 'execute_cypher':
                        result = await self.execute_cypher(arguments.get('query', ''), arguments.get('parameters', {}))
                        return {'success': True, 'result': result[0].text if result else 'No result'}
                    elif tool_name == 'health_check':
                        result = await self.health_check()
                        return {'success': True, 'result': result[0].text if result else 'No result'}
                    else:
                        return {'error': f'Unknown tool: {tool_name}'}
                else:
                    return {'error': f'Unknown method: {method}'}
            else:
                return {'error': 'Invalid request format'}
        except Exception as e:
            logger.error(f"Error processing MCP request: {e}")
            return {'error': str(e)}

async def main():
    """Main entry point"""
    server = Neo4jMCPServer()
    await server.run()

def lambda_handler(event, context):
    """AWS Lambda handler for Neo4j MCP server"""
    try:
        # Initialize the MCP server
        server = Neo4jMCPServer()
        
        # Handle HTTP requests (for Lambda Function URL)
        if 'httpMethod' in event:
            # HTTP request from Lambda Function URL
            body = json.loads(event.get('body', '{}'))
            
            # Route to appropriate handler
            if event['httpMethod'] == 'GET' and event['path'] == '/health':
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'status': 'healthy', 'service': 'neo4j-mcp-server'})
                }
            elif event['httpMethod'] == 'POST' and event['path'] == '/mcp':
                # Handle MCP protocol requests
                result = asyncio.run(server.process_mcp_request(body))
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(result)
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Not found'})
                }
        else:
            # Direct invocation
            return asyncio.run(server.process_mcp_request(event))
            
    except Exception as e:
        logging.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

if __name__ == "__main__":
    asyncio.run(main())
