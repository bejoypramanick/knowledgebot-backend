#!/usr/bin/env python3
"""
Pinecone MCP Server - Correct Implementation
Based on actual Pinecone MCP server with 5 core tools:
- semantic-search: Conducts searches within the Pinecone index
- read-document: Retrieves documents stored in the index  
- list-documents: Lists all documents available in the index
- pinecone-stats: Provides statistics about the index
- process-document: Processes and upserts documents into the index

This server uses natural language instructions and internal tool orchestration
rather than exposing individual API operations as separate tools.
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

# Pinecone imports
from pinecone import Pinecone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeMCPServer:
    """Pinecone MCP Server with 5 core tools for natural language interaction"""
    
    def __init__(self):
        self.server = Server("pinecone-mcp-server")
        self.pc = None
        self.index = None
        self._setup_handlers()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Pinecone client and index"""
        try:
            api_key = os.environ.get('PINECONE_API_KEY')
            index_name = os.environ.get('PINECONE_INDEX_NAME')
            
            if not api_key:
                logger.error("PINECONE_API_KEY environment variable not set")
                return
            
            self.pc = Pinecone(api_key=api_key)
            
            if index_name:
                self.index = self.pc.Index(index_name)
                logger.info(f"✅ Pinecone client initialized with index: {index_name}")
            else:
                logger.info("✅ Pinecone client initialized (no index specified)")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone client: {e}")
            self.pc = None
            self.index = None
    
    def _setup_handlers(self):
        """Setup MCP server handlers with 5 core tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List the 5 core Pinecone MCP tools"""
            return [
                Tool(
                    name="semantic-search",
                    description="Conducts semantic searches within the Pinecone index. Use natural language to describe what you're looking for.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query describing what you want to search for"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 10
                            },
                            "filter": {
                                "type": "object",
                                "description": "Optional metadata filter for the search",
                                "default": {}
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="read-document",
                    description="Retrieves a specific document from the Pinecone index by its ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The ID of the document to retrieve"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                Tool(
                    name="list-documents",
                    description="Lists all documents available in the Pinecone index with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of documents to return",
                                "default": 100
                            },
                            "filter": {
                                "type": "object",
                                "description": "Optional metadata filter for the documents",
                                "default": {}
                            }
                        }
                    }
                ),
                Tool(
                    name="pinecone-stats",
                    description="Provides comprehensive statistics about the Pinecone index including record count, dimensions, and usage metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="process-document",
                    description="Processes and upserts documents into the Pinecone index, including automatic chunking and embedding generation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The text content to process and store"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata to associate with the document",
                                "default": {}
                            },
                            "document_id": {
                                "type": "string",
                                "description": "Optional custom ID for the document. If not provided, a UUID will be generated"
                            },
                            "chunk_size": {
                                "type": "integer",
                                "description": "Size of text chunks for processing",
                                "default": 1000
                            },
                            "chunk_overlap": {
                                "type": "integer",
                                "description": "Overlap between chunks",
                                "default": 200
                            }
                        },
                        "required": ["content"]
                    }
                ),
                Tool(
                    name="get_health",
                    description="Check server health status and connection to Pinecone",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls for the 5 core Pinecone MCP tools"""
            try:
                if name == "semantic-search":
                    return await self._semantic_search(arguments)
                elif name == "read-document":
                    return await self._read_document(arguments)
                elif name == "list-documents":
                    return await self._list_documents(arguments)
                elif name == "pinecone-stats":
                    return await self._pinecone_stats()
                elif name == "process-document":
                    return await self._process_document(arguments)
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
    
    async def _semantic_search(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Conducts semantic searches within the Pinecone index"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            query = arguments.get("query")
            top_k = arguments.get("top_k", 10)
            filter_dict = arguments.get("filter", {})
            
            if not query:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Query is required"
                    })
                )]
            
            # For semantic search, we need to generate embeddings from the query
            # This is where the MCP server would use its internal embedding model
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                query_embedding = model.encode([query])[0].tolist()
            except ImportError:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Embedding model not available. Please install sentence-transformers."
                    })
                )]
            
            # Perform the search
            search_kwargs = {
                "vector": query_embedding,
                "top_k": top_k,
                "include_metadata": True
            }
            
            if filter_dict:
                search_kwargs["filter"] = filter_dict
            
            result = self.index.query(**search_kwargs)
            
            # Format results
            matches = []
            for match in result.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                })
            
            result_data = {
                "success": True,
                "query": query,
                "matches": matches,
                "total_matches": len(matches),
                "index_name": self.index.name if hasattr(self.index, 'name') else 'unknown'
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _read_document(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Retrieves a specific document from the Pinecone index by its ID"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            document_id = arguments.get("document_id")
            if not document_id:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "document_id is required"
                    })
                )]
            
            # Fetch the document by ID
            result = self.index.fetch(ids=[document_id])
            
            if document_id in result.vectors:
                vector_data = result.vectors[document_id]
                document_data = {
                    "success": True,
                    "document_id": document_id,
                    "metadata": vector_data.metadata,
                    "dimensions": len(vector_data.values) if vector_data.values else 0,
                    "found": True
                }
            else:
                document_data = {
                    "success": True,
                    "document_id": document_id,
                    "found": False,
                    "message": "Document not found"
                }
            
            return [TextContent(
                type="text",
                text=json.dumps(document_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error reading document: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _list_documents(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Lists all documents available in the Pinecone index"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            limit = arguments.get("limit", 100)
            filter_dict = arguments.get("filter", {})
            
            # Get index stats first to understand the scope
            stats = self.index.describe_index_stats()
            total_vectors = stats.total_vector_count
            
            # For listing documents, we'll use a scan operation
            # Note: This is a simplified implementation
            # In practice, you might want to implement pagination
            documents = []
            
            # Use query with a zero vector to get some documents
            # This is a workaround since Pinecone doesn't have a direct "list all" operation
            try:
                # Create a zero vector for the query
                zero_vector = [0.0] * 1024  # Assuming 1024 dimensions, adjust as needed
                
                result = self.index.query(
                    vector=zero_vector,
                    top_k=min(limit, 1000),  # Pinecone has limits on top_k
                    include_metadata=True
                )
                
                for match in result.matches:
                    documents.append({
                        "id": match.id,
                        "score": match.score,
                        "metadata": match.metadata
                    })
                
            except Exception as e:
                logger.warning(f"Error during document listing: {e}")
                # Fallback: return stats information
                documents = [{"message": "Unable to list documents directly", "total_vectors": total_vectors}]
            
            result_data = {
                "success": True,
                "documents": documents,
                "total_documents": len(documents),
                "total_vectors_in_index": total_vectors,
                "limit_applied": limit
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _pinecone_stats(self) -> List[TextContent]:
        """Provides comprehensive statistics about the Pinecone index"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            # Get index statistics
            stats = self.index.describe_index_stats()
            
            # Get index description
            index_info = self.pc.describe_index(self.index.name) if hasattr(self.index, 'name') else None
            
            result_data = {
                "success": True,
                "index_stats": {
                    "total_vector_count": stats.total_vector_count,
                    "dimension": stats.dimension,
                    "index_fullness": stats.index_fullness,
                    "namespaces": dict(stats.namespaces) if stats.namespaces else {}
                },
                "index_info": {
                    "name": index_info.name if index_info else "unknown",
                    "dimension": index_info.dimension if index_info else stats.dimension,
                    "metric": index_info.metric if index_info else "unknown",
                    "host": index_info.host if index_info else "unknown",
                    "status": index_info.status.state if index_info and hasattr(index_info.status, 'state') else "unknown"
                } if index_info else None,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error getting Pinecone stats: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _process_document(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Processes and upserts documents into the Pinecone index with chunking and embedding"""
        try:
            if not self.index:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Pinecone index not initialized"
                    })
                )]
            
            content = arguments.get("content")
            metadata = arguments.get("metadata", {})
            document_id = arguments.get("document_id")
            chunk_size = arguments.get("chunk_size", 1000)
            chunk_overlap = arguments.get("chunk_overlap", 200)
            
            if not content:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Content is required"
                    })
                )]
            
            # Generate document ID if not provided
            if not document_id:
                import uuid
                document_id = str(uuid.uuid4())
            
            # Simple text chunking
            chunks = []
            start = 0
            while start < len(content):
                end = min(start + chunk_size, len(content))
                chunk_text = content[start:end]
                
                # Find a good break point (end of sentence or word)
                if end < len(content):
                    # Try to break at sentence end
                    last_period = chunk_text.rfind('.')
                    last_exclamation = chunk_text.rfind('!')
                    last_question = chunk_text.rfind('?')
                    last_break = max(last_period, last_exclamation, last_question)
                    
                    if last_break > chunk_size * 0.5:  # If we found a good break point
                        chunk_text = chunk_text[:last_break + 1]
                        end = start + last_break + 1
                
                chunks.append({
                    "text": chunk_text.strip(),
                    "chunk_id": f"{document_id}_chunk_{len(chunks)}",
                    "start_pos": start,
                    "end_pos": end
                })
                
                start = end - chunk_overlap if end < len(content) else end
            
            # Generate embeddings for chunks
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                
                chunk_texts = [chunk["text"] for chunk in chunks]
                embeddings = model.encode(chunk_texts)
                
                # Prepare vectors for upsert
                vectors = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_metadata = {
                        **metadata,
                        "document_id": document_id,
                        "chunk_id": chunk["chunk_id"],
                        "chunk_index": i,
                        "text": chunk["text"],
                        "start_pos": chunk["start_pos"],
                        "end_pos": chunk["end_pos"]
                    }
                    
                    vectors.append({
                        "id": chunk["chunk_id"],
                        "values": embedding.tolist(),
                        "metadata": chunk_metadata
                    })
                
                # Upsert vectors
                result = self.index.upsert(vectors=vectors)
                
                result_data = {
                    "success": True,
                    "document_id": document_id,
                    "chunks_created": len(chunks),
                    "vectors_upserted": result.upserted_count,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "total_content_length": len(content)
                }
                
            except ImportError:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Embedding model not available. Please install sentence-transformers."
                    })
                )]
            
            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
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
            "status": "healthy" if self.pc and self.index else "unhealthy",
            "client_initialized": self.pc is not None,
            "index_initialized": self.index is not None,
            "server": "pinecone-mcp-server",
            "version": "1.0.0",
            "tools_available": [
                "semantic-search",
                "read-document", 
                "list-documents",
                "pinecone-stats",
                "process-document"
            ],
            "natural_language_support": True
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
