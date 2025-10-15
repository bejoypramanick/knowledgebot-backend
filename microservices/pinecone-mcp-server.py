#!/usr/bin/env python3
"""
Pinecone MCP Server - Based on pinecone-io/pinecone-mcp
Provides vector database operations through MCP protocol
"""

import asyncio
import json
import logging
import os
import traceback
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

# Pinecone imports
from pinecone import Pinecone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeMCPServer:
    """Pinecone MCP Server for vector operations"""
    
    def __init__(self):
        self.server = Server("pinecone-mcp-server")
        self.pc = None
        self.index = None
        self._setup_handlers()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Pinecone client"""
        try:
            api_key = os.environ.get('PINECONE_API_KEY')
            environment = os.environ.get('PINECONE_ENVIRONMENT', 'us-east-1')
            index_name = os.environ.get('PINECONE_INDEX_NAME')
            
            # Get embedding model configuration
            embedding_model_name = os.environ.get('PINECONE_EMBEDDING_MODEL', 'nvidia/llama-text-embed-v2')
            embedding_dimensions = int(os.environ.get('PINECONE_EMBEDDING_DIMENSIONS', '1024'))
            
            if not api_key:
                logger.error("PINECONE_API_KEY environment variable not set")
                return
            
            self.pc = Pinecone(api_key=api_key)
            
            if index_name:
                self.index = self.pc.Index(index_name)
                logger.info(f"✅ Pinecone client initialized with index: {index_name}")
                logger.info(f"🧠 Configured embedding model: {embedding_model_name}")
                logger.info(f"📏 Embedding dimensions: {embedding_dimensions}")
                
                # Store embedding model configuration
                self.embedding_model_name = embedding_model_name
                self.embedding_dimensions = embedding_dimensions
            else:
                logger.info("✅ Pinecone client initialized (no index specified)")
                self.embedding_model_name = embedding_model_name
                self.embedding_dimensions = embedding_dimensions
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone client: {e}")
            self.pc = None
            self.index = None
    
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="query_vectors",
                    description="Query vectors from Pinecone index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vector": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "Query vector"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 10
                            },
                            "filter": {
                                "type": "object",
                                "description": "Metadata filter",
                                "default": {}
                            },
                            "namespace": {
                                "type": "string",
                                "description": "Namespace to query",
                                "default": "default"
                            }
                        },
                        "required": ["vector"]
                    }
                ),
                Tool(
                    name="upsert_vectors",
                    description="Upsert vectors to Pinecone index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vectors": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "values": {
                                            "type": "array",
                                            "items": {"type": "number"}
                                        },
                                        "metadata": {"type": "object"}
                                    },
                                    "required": ["id", "values"]
                                },
                                "description": "Vectors to upsert"
                            },
                            "namespace": {
                                "type": "string",
                                "description": "Namespace to upsert to",
                                "default": "default"
                            }
                        },
                        "required": ["vectors"]
                    }
                ),
                Tool(
                    name="delete_vectors",
                    description="Delete vectors from Pinecone index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Vector IDs to delete"
                            },
                            "namespace": {
                                "type": "string",
                                "description": "Namespace to delete from",
                                "default": "default"
                            }
                        },
                        "required": ["ids"]
                    }
                ),
                Tool(
                    name="get_index_stats",
                    description="Get Pinecone index statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="generate_embeddings",
                    description="Generate embeddings for text using SentenceTransformer",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "texts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of texts to generate embeddings for"
                            }
                        },
                        "required": ["texts"]
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
                if name == "query_vectors":
                    return await self._query_vectors(arguments)
                elif name == "upsert_vectors":
                    return await self._upsert_vectors(arguments)
                elif name == "delete_vectors":
                    return await self._delete_vectors(arguments)
                elif name == "get_index_stats":
                    return await self._get_index_stats()
                elif name == "generate_embeddings":
                    return await self._generate_embeddings(arguments)
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
    
    async def _query_vectors(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Query vectors from Pinecone"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            vector = arguments.get("vector")
            top_k = arguments.get("top_k", 10)
            filter_dict = arguments.get("filter", {})
            namespace = arguments.get("namespace", "default")
            
            if not vector:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Vector is required"
                    })
                )]
            
            # Query the index
            query_kwargs = {
                "vector": vector,
                "top_k": top_k,
                "namespace": namespace if namespace != "default" else None
            }
            
            if filter_dict:
                query_kwargs["filter"] = filter_dict
            
            result = self.index.query(**query_kwargs)
            
            # Format results
            matches = []
            for match in result.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "values": match.values,
                    "metadata": match.metadata
                })
            
            result_data = {
                "success": True,
                "matches": matches,
                "namespace": result.namespace,
                "query_vector_dimension": len(vector)
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error querying vectors: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _upsert_vectors(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Upsert vectors to Pinecone"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            vectors = arguments.get("vectors", [])
            namespace = arguments.get("namespace", "default")
            
            if not vectors:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Vectors are required"
                    })
                )]
            
            # Upsert vectors
            upsert_kwargs = {
                "vectors": vectors,
                "namespace": namespace if namespace != "default" else None
            }
            
            result = self.index.upsert(**upsert_kwargs)
            
            result_data = {
                "success": True,
                "upserted_count": result.upserted_count,
                "namespace": namespace
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error upserting vectors: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _delete_vectors(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Delete vectors from Pinecone"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            ids = arguments.get("ids", [])
            namespace = arguments.get("namespace", "default")
            
            if not ids:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Vector IDs are required"
                    })
                )]
            
            # Delete vectors
            delete_kwargs = {
                "ids": ids,
                "namespace": namespace if namespace != "default" else None
            }
            
            self.index.delete(**delete_kwargs)
            
            result_data = {
                "success": True,
                "deleted_count": len(ids),
                "namespace": namespace
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _get_index_stats(self) -> List[TextContent]:
        """Get index statistics"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            stats = self.index.describe_index_stats()
            
            result_data = {
                "success": True,
                "stats": {
                    "total_vector_count": stats.total_vector_count,
                    "dimension": stats.dimension,
                    "index_fullness": stats.index_fullness,
                    "namespaces": dict(stats.namespaces) if stats.namespaces else {}
                }
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
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
    
    async def _generate_embeddings(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Generate embeddings using Pinecone's native embedding models with comprehensive logging"""
        start_time = datetime.now()
        
        try:
            texts = arguments.get("texts", [])
            logger.info(f"🔄 Starting embedding generation for {len(texts)} texts using Pinecone native models")
            
            # Validate input parameters
            if not texts:
                logger.error("❌ No texts provided for embedding generation")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "No texts provided for embedding generation",
                        "error_type": "ValidationError"
                    })
                )]
            
            if not isinstance(texts, list):
                logger.error("❌ Texts must be a list of strings")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Texts must be a list of strings",
                        "error_type": "ValidationError"
                    })
                )]
            
            if not self.index:
                logger.error("❌ Pinecone index not initialized")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized",
                        "error_type": "ConfigurationError"
                    })
                )]
            
            # Validate and preprocess texts
            valid_texts = []
            for i, text in enumerate(texts):
                if not text or not isinstance(text, str) or text.strip() == "":
                    logger.warning(f"⚠️ Skipping invalid text at index {i}: {repr(text)}")
                    continue
                
                # Truncate very long texts
                if len(text) > 10000:
                    logger.warning(f"⚠️ Truncating long text at index {i} (length: {len(text)})")
                    text = text[:10000]
                
                valid_texts.append(text.strip())
            
            if not valid_texts:
                logger.error("❌ No valid texts found after validation")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "No valid texts found after validation",
                        "error_type": "ValidationError"
                    })
                )]
            
            logger.info(f"📊 Valid texts after filtering: {len(valid_texts)}")
            logger.info(f"📊 Text lengths: {[len(text) for text in valid_texts[:5]]}...")
            
            # Use Pinecone's integrated inference for native embedding generation
            embeddings = []
            successful_embeddings = 0
            failed_embeddings = 0
            
            for i, text in enumerate(valid_texts):
                try:
                    logger.debug(f"🔄 Processing text {i+1}/{len(valid_texts)} (length: {len(text)})")
                    
                    # Query with text input - Pinecone will generate embeddings using native models
                    query_result = self.index.query(
                        vector=text,  # Pass text directly - Pinecone will embed it
                        top_k=1,
                        include_values=True,
                        include_metadata=False
                    )
                    
                    if query_result.matches and len(query_result.matches) > 0:
                        # Extract the generated embedding
                        embedding_vector = query_result.matches[0].values
                        
                        # Validate embedding vector
                        if isinstance(embedding_vector, list) and len(embedding_vector) > 0:
                            embeddings.append({
                                "text": text,
                                "embedding": embedding_vector,
                                "index": i,
                                "dimensions": len(embedding_vector)
                            })
                            successful_embeddings += 1
                            logger.debug(f"✅ Generated embedding {i+1}: {len(embedding_vector)} dimensions")
                        else:
                            logger.warning(f"⚠️ Invalid embedding vector for text {i+1}: {type(embedding_vector)}")
                            embeddings.append({
                                "text": text,
                                "embedding": None,
                                "index": i,
                                "error": "Invalid embedding vector"
                            })
                            failed_embeddings += 1
                    else:
                        logger.warning(f"⚠️ No matches returned for text {i+1}")
                        embeddings.append({
                            "text": text,
                            "embedding": None,
                            "index": i,
                            "error": "No matches returned"
                        })
                        failed_embeddings += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error generating embedding for text {i+1}: {e}")
                    embeddings.append({
                        "text": text,
                        "embedding": None,
                        "index": i,
                        "error": str(e)
                    })
                    failed_embeddings += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result_data = {
                "success": True,
                "embeddings": embeddings,
                "texts_processed": len(valid_texts),
                "successful_embeddings": successful_embeddings,
                "failed_embeddings": failed_embeddings,
                "method": "pinecone_native_integrated_inference",
                "embedding_model": getattr(self, 'embedding_model_name', 'nvidia/llama-text-embed-v2'),
                "embedding_dimensions": getattr(self, 'embedding_dimensions', 1024),
                "processing_time": processing_time,
                "embedding_rate": successful_embeddings / processing_time if processing_time > 0 else 0,
                "note": "Using Pinecone's native embedding model configured at index creation"
            }
            
            logger.info(f"✅ Generated embeddings for {successful_embeddings}/{len(valid_texts)} texts using Pinecone native models")
            logger.info(f"📊 Processing time: {processing_time:.3f}s")
            logger.info(f"📊 Embedding rate: {successful_embeddings / processing_time:.2f} embeddings/sec")
            logger.info(f"📊 Success rate: {(successful_embeddings / len(valid_texts)) * 100:.1f}%")
            
            if failed_embeddings > 0:
                logger.warning(f"⚠️ {failed_embeddings} embeddings failed to generate")
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error generating embeddings: {e}")
            logger.error(f"📊 Error type: {type(e).__name__}")
            logger.error(f"📊 Stack trace: {traceback.format_exc()}")
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": processing_time
                }, indent=2)
            )]

    async def _get_health(self) -> List[TextContent]:
        """Get server health status"""
        status = {
            "status": "healthy" if self.pc and self.index else "unhealthy",
            "client_initialized": self.pc is not None,
            "index_initialized": self.index is not None,
            "server": "pinecone-mcp-server",
            "version": "1.0.0"
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(status, indent=2)
        )]
    
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
                    
                    if tool_name == 'upsert_vectors':
                        result = await self.upsert_vectors(arguments.get('vectors', []), arguments.get('namespace', ''))
                        return {'success': True, 'result': result[0].text if result else 'No result'}
                    elif tool_name == 'query_vectors':
                        result = await self.query_vectors(arguments.get('vector', []), arguments.get('top_k', 10), arguments.get('namespace', ''))
                        return {'success': True, 'result': result[0].text if result else 'No result'}
                    elif tool_name == 'generate_embeddings':
                        result = await self.generate_embeddings(arguments.get('texts', []))
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

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="pinecone-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """Main entry point"""
    server = PineconeMCPServer()
    await server.run()

def lambda_handler(event, context):
    """AWS Lambda handler for Pinecone MCP server"""
    try:
        # Initialize the MCP server
        server = PineconeMCPServer()
        
        # Handle HTTP requests (for Lambda Function URL)
        if 'httpMethod' in event:
            # HTTP request from Lambda Function URL
            body = json.loads(event.get('body', '{}'))
            
            # Route to appropriate handler
            if event['httpMethod'] == 'GET' and event['path'] == '/health':
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'status': 'healthy', 'service': 'pinecone-mcp-server'})
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
