#!/usr/bin/env python3
"""
Docling MCP Client - Client for communicating with the official Docling MCP Server
"""

import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DoclingMCPClient:
    """Client for communicating with the official Docling MCP Server"""
    
    def __init__(self, base_url: str = "http://localhost:3000/mcp"):
        self.base_url = base_url
        self.session = None
        self.request_id = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_jsonrpc_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC call to the Docling MCP server"""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            async with self.session.post(self.base_url, headers=headers, data=json.dumps(payload)) as response:
                response.raise_for_status()
                result = await response.json()
                if "error" in result:
                    logger.error(f"Docling MCP Error: {result['error']}")
                    return {"success": False, "error": result["error"]}
                return {"success": True, "result": result.get("result")}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"success": False, "error": f"Invalid JSON response: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_document(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Process a document using the official Docling MCP server"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "process_document",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename
            }
        })
    
    async def convert_pdf_to_markdown(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Convert PDF to Markdown using the official Docling MCP server"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "convert_pdf_to_markdown",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename
            }
        })
    
    async def convert_document_to_json(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Convert document to structured JSON using the official Docling MCP server"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "convert_document_to_json",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename
            }
        })
    
    async def chunk_document(self, document_bytes: str, filename: str, chunk_size: int = 1000) -> Dict[str, Any]:
        """Chunk a document using the official Docling MCP server"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "chunk_document",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename,
                "chunk_size": chunk_size
            }
        })
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the Docling MCP server"""
        return await self._make_jsonrpc_call("tools/list", {})
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return await self._make_jsonrpc_call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "docling-mcp-client",
                "version": "1.0.0"
            }
        })

# Example usage
async def main():
    """Example usage of the Docling MCP Client"""
    async with DoclingMCPClient() as client:
        # List available tools
        tools_result = await client.list_tools()
        print("Available tools:", json.dumps(tools_result, indent=2))
        
        # Example: Process a document (you would need actual document bytes)
        # document_bytes = base64.b64encode(open("example.pdf", "rb").read()).decode()
        # result = await client.process_document(document_bytes, "example.pdf")
        # print("Document processing result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
