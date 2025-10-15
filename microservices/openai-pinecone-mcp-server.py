#!/usr/bin/env python3
"""
OpenAI + Pinecone MCP Server - Integrates OpenAI with Pinecone MCP server
Uses OpenAI for natural language processing and Pinecone MCP for vector operations
"""

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
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

# OpenAI imports
from openai import OpenAI

# Pinecone MCP client
from pinecone_mcp_client import PineconeMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIPineconeMCPServer:
    """OpenAI MCP Server with Pinecone integration for natural language vector operations"""
    
    def __init__(self):
        self.server = Server("openai-pinecone-mcp-server")
        self.openai_client = None
        self.pinecone_client = None
        self._setup_handlers()
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize OpenAI and Pinecone MCP clients"""
        try:
            # Initialize OpenAI client
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                logger.error("OPENAI_API_KEY environment variable not set")
                return
            
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("✅ OpenAI client initialized successfully")
            
            # Initialize Pinecone MCP client
            pinecone_mcp_url = os.environ.get('PINECONE_MCP_URL', 'http://localhost:3000/mcp')
            self.pinecone_client = PineconeMCPClient(pinecone_mcp_url)
            logger.info(f"✅ Pinecone MCP client initialized: {pinecone_mcp_url}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize clients: {e}")
            self.openai_client = None
            self.pinecone_client = None
    
    def _setup_handlers(self):
        """Setup MCP server handlers with OpenAI + Pinecone tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools combining OpenAI and Pinecone capabilities"""
            return [
                Tool(
                    name="chat_completion",
                    description="Generate chat completions using OpenAI with natural language processing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "messages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                        "content": {"type": "string"}
                                    },
                                    "required": ["role", "content"]
                                },
                                "description": "Array of messages for the conversation"
                            },
                            "model": {
                                "type": "string",
                                "description": "OpenAI model to use",
                                "default": "gpt-4"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum tokens to generate",
                                "default": 1000
                            },
                            "temperature": {
                                "type": "number",
                                "description": "Temperature for response generation",
                                "default": 0.7
                            }
                        },
                        "required": ["messages"]
                    }
                ),
                Tool(
                    name="vector_search",
                    description="Search vector database using natural language queries with OpenAI + Pinecone",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query"
                            },
                            "index_name": {
                                "type": "string",
                                "description": "Pinecone index name to search"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 10
                            },
                            "filter": {
                                "type": "object",
                                "description": "Optional metadata filter",
                                "default": {}
                            }
                        },
                        "required": ["query", "index_name"]
                    }
                ),
                Tool(
                    name="vector_upsert",
                    description="Add documents to vector database using OpenAI for processing and Pinecone for storage",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Text content to add to the vector database"
                            },
                            "index_name": {
                                "type": "string",
                                "description": "Pinecone index name"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata for the document",
                                "default": {}
                            },
                            "document_id": {
                                "type": "string",
                                "description": "Optional custom document ID"
                            }
                        },
                        "required": ["content", "index_name"]
                    }
                ),
                Tool(
                    name="list_indexes",
                    description="List all available Pinecone indexes",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="index_stats",
                    description="Get statistics for a specific Pinecone index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "index_name": {
                                "type": "string",
                                "description": "Name of the index to get stats for"
                            }
                        },
                        "required": ["index_name"]
                    }
                ),
                Tool(
                    name="natural_language_query",
                    description="Process complex natural language queries that may involve both OpenAI reasoning and Pinecone vector operations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Complex natural language query that may require reasoning and vector search"
                            },
                            "context": {
                                "type": "object",
                                "description": "Optional context including index names, filters, etc.",
                                "default": {}
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_health",
                    description="Check health status of OpenAI and Pinecone MCP services",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls for OpenAI + Pinecone operations"""
            try:
                if name == "chat_completion":
                    return await self._chat_completion(arguments)
                elif name == "vector_search":
                    return await self._vector_search(arguments)
                elif name == "vector_upsert":
                    return await self._vector_upsert(arguments)
                elif name == "list_indexes":
                    return await self._list_indexes()
                elif name == "index_stats":
                    return await self._index_stats(arguments)
                elif name == "natural_language_query":
                    return await self._natural_language_query(arguments)
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
    
    async def _chat_completion(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Generate chat completions using OpenAI"""
        try:
            if not self.openai_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "OpenAI client not initialized"
                    })
                )]
            
            messages = arguments.get("messages", [])
            model = arguments.get("model", "gpt-4")
            max_tokens = arguments.get("max_tokens", 1000)
            temperature = arguments.get("temperature", 0.7)
            
            if not messages:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Messages are required"
                    })
                )]
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result_data = {
                "success": True,
                "response": response.choices[0].message.content,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _vector_search(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Search vector database using natural language with OpenAI + Pinecone"""
        try:
            if not self.pinecone_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone MCP client not initialized"
                    })
                )]
            
            query = arguments.get("query")
            index_name = arguments.get("index_name")
            top_k = arguments.get("top_k", 10)
            filter_dict = arguments.get("filter", {})
            
            if not query or not index_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Query and index_name are required"
                    })
                )]
            
            # Use Pinecone MCP client to search
            async with self.pinecone_client as client:
                result = await client.search_records_by_text(
                    index_name=index_name,
                    text_query=query,
                    top_k=top_k,
                    filter_dict=filter_dict
                )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _vector_upsert(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Add documents to vector database using OpenAI + Pinecone"""
        try:
            if not self.pinecone_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone MCP client not initialized"
                    })
                )]
            
            content = arguments.get("content")
            index_name = arguments.get("index_name")
            metadata = arguments.get("metadata", {})
            document_id = arguments.get("document_id")
            
            if not content or not index_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Content and index_name are required"
                    })
                )]
            
            # Generate document ID if not provided
            if not document_id:
                import uuid
                document_id = str(uuid.uuid4())
            
            # Prepare record for upsert
            record = {
                "id": document_id,
                "text": content,
                "metadata": {
                    **metadata,
                    "created_at": datetime.now().isoformat(),
                    "content_length": len(content)
                }
            }
            
            # Use Pinecone MCP client to upsert
            async with self.pinecone_client as client:
                result = await client.upsert_records(
                    index_name=index_name,
                    records=[record]
                )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error in vector upsert: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _list_indexes(self) -> List[TextContent]:
        """List all Pinecone indexes"""
        try:
            if not self.pinecone_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone MCP client not initialized"
                    })
                )]
            
            async with self.pinecone_client as client:
                result = await client.list_indexes()
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error listing indexes: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _index_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get statistics for a specific index"""
        try:
            if not self.pinecone_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone MCP client not initialized"
                    })
                )]
            
            index_name = arguments.get("index_name")
            if not index_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "index_name is required"
                    })
                )]
            
            async with self.pinecone_client as client:
                result = await client.describe_index_stats(index_name)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _natural_language_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Process complex natural language queries using OpenAI + Pinecone"""
        try:
            if not self.openai_client or not self.pinecone_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "OpenAI or Pinecone client not initialized"
                    })
                )]
            
            query = arguments.get("query")
            context = arguments.get("context", {})
            
            if not query:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Query is required"
                    })
                )]
            
            # Use OpenAI to analyze the query and determine what vector operations are needed
            analysis_prompt = f"""
            Analyze this natural language query and determine what vector database operations are needed:
            
            Query: "{query}"
            Available context: {json.dumps(context, indent=2)}
            
            Available operations:
            1. list_indexes - List all available indexes
            2. search_records - Search for similar content
            3. index_stats - Get statistics about an index
            4. upsert_records - Add new content
            
            Respond with a JSON object containing:
            - operation: the operation to perform
            - parameters: the parameters needed for the operation
            - reasoning: why this operation is needed
            """
            
            analysis_response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes queries and determines appropriate vector database operations."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            analysis = json.loads(analysis_response.choices[0].message.content)
            
            # Execute the determined operation
            operation = analysis.get("operation")
            parameters = analysis.get("parameters", {})
            
            result = {"analysis": analysis}
            
            async with self.pinecone_client as client:
                if operation == "list_indexes":
                    result["operation_result"] = await client.list_indexes()
                elif operation == "search_records":
                    result["operation_result"] = await client.search_records_by_text(**parameters)
                elif operation == "index_stats":
                    result["operation_result"] = await client.describe_index_stats(**parameters)
                elif operation == "upsert_records":
                    result["operation_result"] = await client.upsert_records(**parameters)
                else:
                    result["operation_result"] = {"error": f"Unknown operation: {operation}"}
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error in natural language query: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _get_health(self) -> List[TextContent]:
        """Get health status of both services"""
        health_status = {
            "openai_client": self.openai_client is not None,
            "pinecone_client": self.pinecone_client is not None,
            "server": "openai-pinecone-mcp-server",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
        # Test Pinecone MCP connection if available
        if self.pinecone_client:
            try:
                async with self.pinecone_client as client:
                    pinecone_health = await client.get_health()
                    health_status["pinecone_mcp_health"] = pinecone_health
            except Exception as e:
                health_status["pinecone_mcp_health"] = {"error": str(e)}
        
        return [TextContent(
            type="text",
            text=json.dumps(health_status, indent=2)
        )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openai-pinecone-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """Main entry point"""
    server = OpenAIPineconeMCPServer()
    await server.run()

def lambda_handler(event, context):
    """AWS Lambda handler for OpenAI + Pinecone MCP server"""
    try:
        # Initialize the MCP server
        server = OpenAIPineconeMCPServer()
        
        # Handle HTTP requests (for Lambda Function URL)
        if 'httpMethod' in event:
            # HTTP request from Lambda Function URL
            body = json.loads(event.get('body', '{}'))
            
            # Route to appropriate handler
            if event['httpMethod'] == 'GET' and event['path'] == '/health':
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'status': 'healthy', 'service': 'openai-pinecone-mcp-server'})
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
