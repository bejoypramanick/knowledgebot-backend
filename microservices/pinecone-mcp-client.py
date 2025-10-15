#!/usr/bin/env python3
"""
Pinecone MCP Client - Communicates with official Pinecone MCP server
Handles JSON-RPC calls to the Pinecone MCP server running via NPM package
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

class PineconeMCPClient:
    """Client for communicating with Pinecone MCP server via JSON-RPC"""
    
    def __init__(self, pinecone_mcp_url: str = None):
        self.pinecone_mcp_url = pinecone_mcp_url or os.environ.get(
            'PINECONE_MCP_URL', 
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
        """Make a JSON-RPC call to the Pinecone MCP server"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {}
            }
            
            logger.info(f"Making JSON-RPC call to {self.pinecone_mcp_url}: {method}")
            
            async with self.session.post(
                self.pinecone_mcp_url,
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
    
    async def list_indexes(self) -> Dict[str, Any]:
        """List all Pinecone indexes"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "list-indexes",
            "arguments": {}
        })
    
    async def describe_index(self, index_name: str) -> Dict[str, Any]:
        """Describe a specific index"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "describe-index",
            "arguments": {
                "index_name": index_name
            }
        })
    
    async def describe_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get statistics for a specific index"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "describe-index-stats",
            "arguments": {
                "index_name": index_name
            }
        })
    
    async def upsert_records(self, index_name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert records to an index"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "upsert-records",
            "arguments": {
                "index_name": index_name,
                "records": records
            }
        })
    
    async def search_records(self, index_name: str, query: List[float], top_k: int = 10, filter_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search records in an index using vector query"""
        args = {
            "index_name": index_name,
            "query": query,
            "top_k": top_k
        }
        if filter_dict:
            args["filter"] = filter_dict
        
        return await self._make_jsonrpc_call("tools/call", {
            "name": "search-records",
            "arguments": args
        })
    
    async def search_records_by_text(self, index_name: str, text_query: str, top_k: int = 10, filter_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search records using text query (requires integrated inference)"""
        args = {
            "index_name": index_name,
            "query": text_query,
            "top_k": top_k
        }
        if filter_dict:
            args["filter"] = filter_dict
        
        return await self._make_jsonrpc_call("tools/call", {
            "name": "search-records",
            "arguments": args
        })
    
    async def delete_records(self, index_name: str, ids: List[str]) -> Dict[str, Any]:
        """Delete records from an index"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "delete-records",
            "arguments": {
                "index_name": index_name,
                "ids": ids
            }
        })
    
    async def get_health(self) -> Dict[str, Any]:
        """Check Pinecone MCP server health"""
        return await self._make_jsonrpc_call("tools/call", {
            "name": "get_health",
            "arguments": {}
        })

# Example usage and testing
async def test_pinecone_mcp_client():
    """Test the Pinecone MCP client"""
    async with PineconeMCPClient() as client:
        # Test health check
        health = await client.get_health()
        print("Health check:", json.dumps(health, indent=2))
        
        # Test list indexes
        indexes = await client.list_indexes()
        print("Indexes:", json.dumps(indexes, indent=2))

if __name__ == "__main__":
    asyncio.run(test_pinecone_mcp_client())
