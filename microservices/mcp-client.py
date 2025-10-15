#!/usr/bin/env python3
"""
Universal MCP Client - Communicates with multiple MCP servers
Handles JSON-RPC calls to various MCP servers (Pinecone, DynamoDB, etc.)
"""

import json
import logging
import os
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalMCPClient:
    """Universal client for communicating with multiple MCP servers via JSON-RPC"""
    
    def __init__(self, 
                 pinecone_mcp_url: str = None,
                 dynamodb_mcp_url: str = None,
                 docling_mcp_url: str = None,
                 neo4j_cypher_mcp_url: str = None,
                 neo4j_modeling_mcp_url: str = None):
        
        self.mcp_servers = {
            "pinecone": pinecone_mcp_url or os.environ.get('PINECONE_MCP_URL', 'http://localhost:3000/mcp'),
            "dynamodb": dynamodb_mcp_url or os.environ.get('DYNAMODB_MCP_URL', 'http://localhost:3001/mcp'),
            "docling": docling_mcp_url or os.environ.get('DOCLING_MCP_URL', 'http://localhost:3002/mcp'),
            "neo4j-cypher": neo4j_cypher_mcp_url or os.environ.get('NEO4J_CYPHER_MCP_URL', 'http://localhost:3003/mcp'),
            "neo4j-modeling": neo4j_modeling_mcp_url or os.environ.get('NEO4J_MODELING_MCP_URL', 'http://localhost:3004/mcp')
        }
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_jsonrpc_call(self, server: str, method: str, params: Dict[str, Any] = None, request_id: int = 1) -> Dict[str, Any]:
        """Make a JSON-RPC call to a specific MCP server"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            if server not in self.mcp_servers:
                return {
                    "error": {
                        "code": -1,
                        "message": f"Unknown MCP server: {server}. Available: {list(self.mcp_servers.keys())}"
                    }
                }
            
            url = self.mcp_servers[server]
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {}
            }
            
            logger.info(f"Making JSON-RPC call to {server} ({url}): {method}")
            
            async with self.session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"JSON-RPC call successful: {server}:{method}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"JSON-RPC call failed: {server}:{method} - {response.status} - {error_text}")
                    return {
                        "error": {
                            "code": response.status,
                            "message": f"HTTP {response.status}: {error_text}"
                        }
                    }
        
        except Exception as e:
            logger.error(f"Error making JSON-RPC call to {server}:{method}: {e}")
            return {
                "error": {
                    "code": -1,
                    "message": str(e)
                }
            }
    
    # Pinecone MCP operations
    async def pinecone_list_indexes(self) -> Dict[str, Any]:
        """List all Pinecone indexes"""
        return await self._make_jsonrpc_call("pinecone", "tools/call", {
            "name": "list-indexes",
            "arguments": {}
        })
    
    async def pinecone_search(self, index_name: str, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Search Pinecone index with text query"""
        return await self._make_jsonrpc_call("pinecone", "tools/call", {
            "name": "search-records",
            "arguments": {
                "index_name": index_name,
                "query": query,
                "top_k": top_k
            }
        })
    
    async def pinecone_upsert(self, index_name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert records to Pinecone index"""
        return await self._make_jsonrpc_call("pinecone", "tools/call", {
            "name": "upsert-records",
            "arguments": {
                "index_name": index_name,
                "records": records
            }
        })
    
    # DynamoDB MCP operations
    async def dynamodb_list_tables(self, limit: int = 10) -> Dict[str, Any]:
        """List all DynamoDB tables"""
        return await self._make_jsonrpc_call("dynamodb", "tools/call", {
            "name": "list-tables",
            "arguments": {
                "limit": limit
            }
        })
    
    async def dynamodb_put_item(self, table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Put item in DynamoDB table"""
        return await self._make_jsonrpc_call("dynamodb", "tools/call", {
            "name": "put-item",
            "arguments": {
                "tableName": table_name,
                "item": item
            }
        })
    
    async def dynamodb_get_item(self, table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
        """Get item from DynamoDB table"""
        return await self._make_jsonrpc_call("dynamodb", "tools/call", {
            "name": "get-item",
            "arguments": {
                "tableName": table_name,
                "key": key
            }
        })
    
    async def dynamodb_scan(self, table_name: str, filter_expression: str = None, 
                           expression_attribute_values: Dict[str, Any] = None, 
                           limit: int = None) -> Dict[str, Any]:
        """Scan DynamoDB table"""
        args = {"tableName": table_name}
        if filter_expression:
            args["filterExpression"] = filter_expression
        if expression_attribute_values:
            args["expressionAttributeValues"] = expression_attribute_values
        if limit:
            args["limit"] = limit
        
        return await self._make_jsonrpc_call("dynamodb", "tools/call", {
            "name": "scan",
            "arguments": args
        })
    
    # Docling MCP operations
    async def docling_process_document(self, content: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process document with Docling"""
        return await self._make_jsonrpc_call("docling", "tools/call", {
            "name": "process_document",
            "arguments": {
                "content": content,
                "options": options or {}
            }
        })
    
    # Neo4j Cypher MCP operations
    async def neo4j_execute_query(self, cypher: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Cypher query on Neo4j using the official Neo4j Cypher MCP server"""
        return await self._make_jsonrpc_call("neo4j-cypher", "tools/call", {
            "name": "execute_query",
            "arguments": {
                "cypher": cypher,
                "parameters": parameters or {}
            }
        })
    
    async def neo4j_list_nodes(self, label: str = None, limit: int = 100) -> Dict[str, Any]:
        """List nodes from Neo4j"""
        cypher = f"MATCH (n{f':{label}' if label else ''}) RETURN n LIMIT {limit}"
        return await self.neo4j_execute_query(cypher)
    
    async def neo4j_list_relationships(self, relationship_type: str = None, limit: int = 100) -> Dict[str, Any]:
        """List relationships from Neo4j"""
        cypher = f"MATCH ()-[r{f':{relationship_type}' if relationship_type else ''}]->() RETURN r LIMIT {limit}"
        return await self.neo4j_execute_query(cypher)
    
    async def neo4j_get_schema(self) -> Dict[str, Any]:
        """Get Neo4j database schema"""
        cypher = "CALL db.schema.visualization()"
        return await self.neo4j_execute_query(cypher)
    
    # Neo4j Data Modeling MCP operations
    async def neo4j_create_node(self, label: str, properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a node in Neo4j using data modeling MCP server"""
        return await self._make_jsonrpc_call("neo4j-modeling", "tools/call", {
            "name": "create_node",
            "arguments": {
                "label": label,
                "properties": properties or {}
            }
        })
    
    async def neo4j_create_relationship(self, from_node: Dict[str, Any], to_node: Dict[str, Any], 
                                      relationship_type: str, properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a relationship in Neo4j using data modeling MCP server"""
        return await self._make_jsonrpc_call("neo4j-modeling", "tools/call", {
            "name": "create_relationship",
            "arguments": {
                "from_node": from_node,
                "to_node": to_node,
                "relationship_type": relationship_type,
                "properties": properties or {}
            }
        })
    
    async def neo4j_validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Neo4j schema using data modeling MCP server"""
        return await self._make_jsonrpc_call("neo4j-modeling", "tools/call", {
            "name": "validate_schema",
            "arguments": {
                "schema": schema
            }
        })
    
    # Docling MCP operations
    async def docling_process_document(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Process a document using the official Docling MCP server"""
        return await self._make_jsonrpc_call("docling", "tools/call", {
            "name": "process_document",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename
            }
        })
    
    async def docling_convert_pdf_to_markdown(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Convert PDF to Markdown using the official Docling MCP server"""
        return await self._make_jsonrpc_call("docling", "tools/call", {
            "name": "convert_pdf_to_markdown",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename
            }
        })
    
    async def docling_convert_document_to_json(self, document_bytes: str, filename: str) -> Dict[str, Any]:
        """Convert document to structured JSON using the official Docling MCP server"""
        return await self._make_jsonrpc_call("docling", "tools/call", {
            "name": "convert_document_to_json",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename
            }
        })
    
    async def docling_chunk_document(self, document_bytes: str, filename: str, chunk_size: int = 1000) -> Dict[str, Any]:
        """Chunk a document using the official Docling MCP server"""
        return await self._make_jsonrpc_call("docling", "tools/call", {
            "name": "chunk_document",
            "arguments": {
                "document_bytes": document_bytes,
                "filename": filename,
                "chunk_size": chunk_size
            }
        })
    
    async def docling_list_tools(self) -> Dict[str, Any]:
        """List available tools from the Docling MCP server"""
        return await self._make_jsonrpc_call("docling", "tools/list", {})
    
    # Health checks
    async def get_health(self, server: str = None) -> Dict[str, Any]:
        """Get health status of MCP servers"""
        if server:
            return await self._make_jsonrpc_call(server, "tools/call", {
                "name": "get_health",
                "arguments": {}
            })
        else:
            health_status = {}
            for server_name in self.mcp_servers.keys():
                try:
                    health_status[server_name] = await self.get_health(server_name)
                except Exception as e:
                    health_status[server_name] = {"error": str(e)}
            return health_status

# Example usage and testing
async def test_mcp_client():
    """Test the universal MCP client"""
    async with UniversalMCPClient() as client:
        # Test health check
        health = await client.get_health()
        print("Health check:", json.dumps(health, indent=2))
        
        # Test Pinecone operations
        try:
            indexes = await client.pinecone_list_indexes()
            print("Pinecone indexes:", json.dumps(indexes, indent=2))
        except Exception as e:
            print(f"Pinecone test failed: {e}")
        
        # Test DynamoDB operations
        try:
            tables = await client.dynamodb_list_tables()
            print("DynamoDB tables:", json.dumps(tables, indent=2))
        except Exception as e:
            print(f"DynamoDB test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_client())
