#!/usr/bin/env python3
"""
Docling MCP Server Handler - Lambda wrapper for official Docling MCP Server
This handler runs the official Docling MCP server using uvx
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DoclingMCPHandler:
    """Lambda handler for official Docling MCP Server"""
    
    def __init__(self):
        self.mcp_process = None
        self._start_mcp_server()
    
    def _start_mcp_server(self):
        """Start the official Docling MCP server using uvx"""
        try:
            # Start the official Docling MCP server
            self.mcp_process = subprocess.Popen(
                ["uvx", "--from=docling-mcp", "docling-mcp-server", "--transport", "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info("Official Docling MCP server started successfully")
        except Exception as e:
            logger.error(f"Failed to start Docling MCP server: {e}")
            raise
    
    async def _send_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the Docling MCP server"""
        if not self.mcp_process:
            raise RuntimeError("MCP server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            # Send request to MCP server
            self.mcp_process.stdin.write(json.dumps(request) + "\n")
            self.mcp_process.stdin.flush()
            
            # Read response
            response_line = self.mcp_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                return response
            else:
                raise RuntimeError("No response from MCP server")
                
        except Exception as e:
            logger.error(f"Error communicating with MCP server: {e}")
            raise
    
    async def process_document(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Process a document using the official Docling MCP server"""
        try:
            response = await self._send_mcp_request("tools/call", {
                "name": "process_document",
                "arguments": {
                    "document_bytes": document_bytes,
                    "filename": filename
                }
            })
            return response
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {"error": str(e)}
    
    async def convert_pdf_to_markdown(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Convert PDF to Markdown using the official Docling MCP server"""
        try:
            response = await self._send_mcp_request("tools/call", {
                "name": "convert_pdf_to_markdown",
                "arguments": {
                    "document_bytes": document_bytes,
                    "filename": filename
                }
            })
            return response
        except Exception as e:
            logger.error(f"Error converting PDF to Markdown: {e}")
            return {"error": str(e)}
    
    async def convert_document_to_json(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Convert document to structured JSON using the official Docling MCP server"""
        try:
            response = await self._send_mcp_request("tools/call", {
                "name": "convert_document_to_json",
                "arguments": {
                    "document_bytes": document_bytes,
                    "filename": filename
                }
            })
            return response
        except Exception as e:
            logger.error(f"Error converting document to JSON: {e}")
            return {"error": str(e)}
    
    async def chunk_document(self, document_bytes: str, filename: str, chunk_size: int = 1000) -> Dict[str, Any]:
        """Chunk a document using the official Docling MCP server"""
        try:
            response = await self._send_mcp_request("tools/call", {
                "name": "chunk_document",
                "arguments": {
                    "document_bytes": document_bytes,
                    "filename": filename,
                    "chunk_size": chunk_size
                }
            })
            return response
        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            return {"error": str(e)}
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the Docling MCP server"""
        try:
            response = await self._send_mcp_request("tools/list", {})
            return response
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Clean up the MCP server process"""
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process.wait()
            self.mcp_process = None

# Global handler instance
handler = DoclingMCPHandler()

def lambda_handler(event, context):
    """
    AWS Lambda handler for Docling MCP Server (synchronous wrapper)
    """
    import asyncio
    
    async def async_handler():
        try:
            # Parse the incoming request
            if isinstance(event, str):
                event = json.loads(event)
            
            # Extract method and parameters
            method = event.get("method", "process_document")
            params = event.get("params", {})
            
            # Route to appropriate method
            if method == "process_document":
                result = await handler.process_document(
                    params.get("document_bytes", ""),
                    params.get("filename", "document.pdf")
                )
            elif method == "convert_pdf_to_markdown":
                result = await handler.convert_pdf_to_markdown(
                    params.get("document_bytes", ""),
                    params.get("filename", "document.pdf")
                )
            elif method == "convert_document_to_json":
                result = await handler.convert_document_to_json(
                    params.get("document_bytes", ""),
                    params.get("filename", "document.pdf")
                )
            elif method == "chunk_document":
                result = await handler.chunk_document(
                    params.get("document_bytes", ""),
                    params.get("filename", "document.pdf"),
                    params.get("chunk_size", 1000)
                )
            elif method == "list_tools":
                result = await handler.list_tools()
            else:
                result = {"error": f"Unknown method: {method}"}
            
            # Return the result
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                },
                "body": json.dumps(result)
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": str(e)})
            }
    
    # Run the async handler
    return asyncio.run(async_handler())

# For local testing
if __name__ == "__main__":
    async def test_handler():
        # Test the handler
        test_event = {
            "method": "list_tools",
            "params": {}
        }
        
        result = await lambda_handler(test_event, None)
        print(json.dumps(result, indent=2))
        
        # Cleanup
        handler.cleanup()
    
    asyncio.run(test_handler())