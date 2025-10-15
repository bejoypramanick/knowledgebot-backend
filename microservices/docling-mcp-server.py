#!/usr/bin/env python3
"""
Docling MCP Server - Based on docling-project/docling-mcp
Provides document processing capabilities through MCP protocol
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path
import tempfile
import base64

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
    ImageContent,
    EmbeddedResource,
)

# Docling imports
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.document import DsDocument
from docling.chunking import HybridChunker
from docling.datamodel.chunking import ChunkingOptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DoclingMCPServer:
    """Docling MCP Server for document processing"""
    
    def __init__(self):
        self.server = Server("docling-mcp-server")
        self.converter = None
        self.chunker = None
        self._setup_handlers()
        self._initialize_converter()
        self._initialize_chunker()
    
    def _initialize_converter(self):
        """Initialize Docling document converter"""
        try:
            # Configure PDF pipeline options
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = True
            pdf_options.do_table_structure = True
            pdf_options.table_structure_options.do_cell_matching = True
            
            # Initialize converter
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pdf_options,
                }
            )
            logger.info("✅ Docling converter initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docling converter: {e}")
            self.converter = None
    
    def _initialize_chunker(self):
        """Initialize Docling HybridChunker"""
        try:
            # Configure chunking options
            chunking_options = ChunkingOptions(
                chunk_size=1000,
                chunk_overlap=200,
                min_chunk_size=100,
                max_chunk_size=2000
            )
            
            # Initialize HybridChunker
            self.chunker = HybridChunker(chunking_options)
            logger.info("✅ Docling HybridChunker initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docling chunker: {e}")
            self.chunker = None
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="process_document",
                    description="Process a document using Docling and extract structured content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_data": {
                                "type": "string",
                                "description": "Base64 encoded document data"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Original filename with extension"
                            },
                            "options": {
                                "type": "object",
                                "description": "Processing options",
                                "properties": {
                                    "format": {
                                        "type": "string",
                                        "enum": ["markdown", "text", "html"],
                                        "default": "markdown"
                                    },
                                    "include_metadata": {
                                        "type": "boolean",
                                        "default": True
                                    },
                                    "use_native_chunking": {
                                        "type": "boolean",
                                        "description": "Use Docling's native HybridChunker for intelligent chunking",
                                        "default": True
                                    },
                                    "chunk_size": {
                                        "type": "integer",
                                        "description": "Target chunk size (for native chunking)",
                                        "default": 1000
                                    },
                                    "chunk_overlap": {
                                        "type": "integer",
                                        "description": "Chunk overlap (for native chunking)",
                                        "default": 200
                                    },
                                    "min_chunk_size": {
                                        "type": "integer",
                                        "description": "Minimum chunk size (for native chunking)",
                                        "default": 100
                                    },
                                    "max_chunk_size": {
                                        "type": "integer",
                                        "description": "Maximum chunk size (for native chunking)",
                                        "default": 2000
                                    }
                                }
                            }
                        },
                        "required": ["document_data", "filename"]
                    }
                ),
                Tool(
                    name="chunk_document",
                    description="Chunk a document using Docling's native HybridChunker",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_data": {
                                "type": "string",
                                "description": "Base64 encoded document data"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Original filename with extension"
                            },
                            "chunking_options": {
                                "type": "object",
                                "description": "Chunking configuration",
                                "properties": {
                                    "chunk_size": {
                                        "type": "integer",
                                        "default": 1000
                                    },
                                    "chunk_overlap": {
                                        "type": "integer",
                                        "default": 200
                                    },
                                    "min_chunk_size": {
                                        "type": "integer",
                                        "default": 100
                                    },
                                    "max_chunk_size": {
                                        "type": "integer",
                                        "default": 2000
                                    }
                                }
                            }
                        },
                        "required": ["document_data", "filename"]
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
                if name == "process_document":
                    return await self._process_document(arguments)
                elif name == "chunk_document":
                    return await self._chunk_document(arguments)
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
    
    async def _process_document(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Process document using Docling"""
        try:
            if not self.converter:
                return [TextContent(
                    type="text",
                    text="Error: Docling converter not initialized"
                )]
            
            # Extract arguments
            document_data = arguments.get("document_data")
            filename = arguments.get("filename")
            options = arguments.get("options", {})
            
            if not document_data or not filename:
                return [TextContent(
                    type="text",
                    text="Error: Missing required arguments: document_data and filename"
                )]
            
            # Decode document data
            try:
                document_bytes = base64.b64decode(document_data)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error decoding document data: {e}"
                )]
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                temp_file.write(document_bytes)
                temp_path = temp_file.name
            
            try:
                # Process document with Docling
                doc = self.converter.convert(temp_path)
                
                # Extract content based on format
                format_type = options.get("format", "markdown")
                if format_type == "markdown":
                    content = doc.export_to_markdown()
                elif format_type == "html":
                    content = doc.export_to_html()
                else:
                    content = doc.export_to_text()
                
                # Create chunks using Docling's native chunking or basic chunking
                chunks = []
                if options.get("use_native_chunking", True) and self.chunker:
                    chunks = self._create_native_chunks(doc, options)
                elif options.get("chunk_size"):
                    chunks = self._create_basic_chunks(content, options.get("chunk_size", 1000), options.get("chunk_overlap", 200))
                
                # Prepare result
                result = {
                    "success": True,
                    "content": {
                        "text": content,
                        "format": format_type
                    },
                    "chunks": chunks,
                    "metadata": {
                        "filename": filename,
                        "page_count": len(doc.pages) if hasattr(doc, 'pages') else 0,
                        "total_chunks": len(chunks)
                    },
                    "statistics": {
                        "total_chunks": len(chunks),
                        "content_length": len(content)
                    }
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    async def _chunk_document(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Chunk document using Docling's native chunking"""
        try:
            if not self.converter or not self.chunker:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Docling converter or chunker not initialized"
                    })
                )]
            
            # Extract arguments
            document_data = arguments.get("document_data")
            filename = arguments.get("filename")
            chunking_options = arguments.get("chunking_options", {})
            
            if not document_data or not filename:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Missing required arguments: document_data and filename"
                    })
                )]
            
            # Decode document data
            try:
                document_bytes = base64.b64decode(document_data)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Error decoding document data: {e}"
                    })
                )]
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                temp_file.write(document_bytes)
                temp_path = temp_file.name
            
            try:
                # Convert document with Docling
                doc = self.converter.convert(temp_path)
                
                # Create chunks using native chunking
                chunks = self._create_native_chunks(doc, chunking_options)
                
                # Prepare result
                result = {
                    "success": True,
                    "chunks": chunks,
                    "metadata": {
                        "filename": filename,
                        "page_count": len(doc.pages) if hasattr(doc, 'pages') else 0,
                        "total_chunks": len(chunks),
                        "chunking_method": "native_hybrid"
                    },
                    "statistics": {
                        "total_chunks": len(chunks),
                        "chunking_options": chunking_options
                    }
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
            )]
    
    def _create_native_chunks(self, doc: DsDocument, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks using Docling's native HybridChunker"""
        try:
            # Update chunker options if provided
            if any(key in options for key in ['chunk_size', 'chunk_overlap', 'min_chunk_size', 'max_chunk_size']):
                chunking_options = ChunkingOptions(
                    chunk_size=options.get('chunk_size', 1000),
                    chunk_overlap=options.get('chunk_overlap', 200),
                    min_chunk_size=options.get('min_chunk_size', 100),
                    max_chunk_size=options.get('max_chunk_size', 2000)
                )
                self.chunker = HybridChunker(chunking_options)
            
            # Use Docling's native chunking
            chunked_doc = self.chunker.chunk(doc)
            
            chunks = []
            for i, chunk in enumerate(chunked_doc.chunks):
                chunk_data = {
                    "id": f"chunk_{i}",
                    "text": chunk.text,
                    "index": i,
                    "chunk_type": "native_hybrid",
                    "metadata": {
                        "chunk_id": getattr(chunk, 'id', f"chunk_{i}"),
                        "page_number": getattr(chunk, 'page_number', None),
                        "bbox": getattr(chunk, 'bbox', None),
                        "element_type": getattr(chunk, 'element_type', None),
                        "element_id": getattr(chunk, 'element_id', None)
                    }
                }
                
                # Add any additional chunk attributes
                if hasattr(chunk, 'tokens'):
                    chunk_data["metadata"]["token_count"] = len(chunk.tokens)
                if hasattr(chunk, 'confidence'):
                    chunk_data["metadata"]["confidence"] = chunk.confidence
                
                chunks.append(chunk_data)
            
            logger.info(f"✅ Created {len(chunks)} chunks using Docling's native HybridChunker")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Error in native chunking: {e}")
            # Fallback to basic chunking
            return self._create_basic_chunks(doc.export_to_text(), options.get('chunk_size', 1000), options.get('chunk_overlap', 200))
    
    def _create_basic_chunks(self, text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        """Create basic text chunks with overlap (fallback method)"""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            chunks.append({
                "id": f"chunk_{chunk_index}",
                "text": chunk_text,
                "start": start,
                "end": end,
                "index": chunk_index,
                "chunk_type": "basic_text"
            })
            
            start = end - chunk_overlap
            chunk_index += 1
            
            if start >= len(text):
                break
        
        logger.info(f"✅ Created {len(chunks)} chunks using basic text chunking")
        return chunks
    
    async def _get_health(self) -> List[TextContent]:
        """Get server health status"""
        status = {
            "status": "healthy" if (self.converter and self.chunker) else "unhealthy",
            "converter_initialized": self.converter is not None,
            "chunker_initialized": self.chunker is not None,
            "native_chunking_available": self.chunker is not None,
            "server": "docling-mcp-server",
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
                    
                    if tool_name == 'process_document':
                        return await self.process_document(arguments.get('document_bytes', ''), arguments.get('filename', ''))
                    elif tool_name == 'health_check':
                        return {'status': 'healthy', 'service': 'docling-mcp-server'}
                    else:
                        return {'error': f'Unknown tool: {tool_name}'}
                else:
                    return {'error': f'Unknown method: {method}'}
            else:
                return {'error': 'Invalid request format'}
        except Exception as e:
            logging.error(f"Error processing MCP request: {e}")
            return {'error': str(e)}

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="docling-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """Main entry point"""
    server = DoclingMCPServer()
    await server.run()

def lambda_handler(event, context):
    """AWS Lambda handler for Docling MCP server"""
    try:
        # Initialize the MCP server
        server = DoclingMCPServer()
        
        # Handle HTTP requests (for Lambda Function URL)
        if 'httpMethod' in event:
            # HTTP request from Lambda Function URL
            body = json.loads(event.get('body', '{}'))
            headers = event.get('headers', {})
            
            # Route to appropriate handler
            if event['httpMethod'] == 'GET' and event['path'] == '/health':
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'status': 'healthy', 'service': 'docling-mcp-server'})
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
