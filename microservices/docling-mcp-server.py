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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DoclingMCPServer:
    """Docling MCP Server for document processing"""
    
    def __init__(self):
        self.server = Server("docling-mcp-server")
        self.converter = None
        self._setup_handlers()
        self._initialize_converter()
    
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
                                    "chunk_size": {
                                        "type": "integer",
                                        "default": 1000
                                    },
                                    "chunk_overlap": {
                                        "type": "integer",
                                        "default": 200
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
                
                # Create chunks if requested
                chunks = []
                if options.get("chunk_size"):
                    chunks = self._create_chunks(content, options.get("chunk_size", 1000), options.get("chunk_overlap", 200))
                
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
    
    def _create_chunks(self, text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        """Create text chunks with overlap"""
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
                "index": chunk_index
            })
            
            start = end - chunk_overlap
            chunk_index += 1
            
            if start >= len(text):
                break
        
        return chunks
    
    async def _get_health(self) -> List[TextContent]:
        """Get server health status"""
        status = {
            "status": "healthy" if self.converter else "unhealthy",
            "converter_initialized": self.converter is not None,
            "server": "docling-mcp-server",
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

if __name__ == "__main__":
    asyncio.run(main())
