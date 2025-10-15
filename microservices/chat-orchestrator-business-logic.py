#!/usr/bin/env python3
"""
Chat Orchestrator Business Logic - Zip Lambda
Orchestrates chat and query processing using Universal MCP Client
Handles user queries and coordinates MCP servers for RAG pipeline
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import Universal MCP Client
from mcp_client import UniversalMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_chat_query_with_mcp(query: str, user_id: str = None) -> Dict[str, Any]:
    """
    Process chat query using MCP servers for RAG pipeline
    """
    try:
        async with UniversalMCPClient() as mcp_client:
            logger.info(f"🚀 Starting chat query processing: {query[:100]}...")
            
            # Step 1: Vector search with Pinecone MCP Server
            logger.info("🔍 Performing vector search with Pinecone MCP Server")
            pinecone_result = await mcp_client.pinecone_search(
                index_name="knowledgebot-index",
                query=query,
                top_k=10
            )
            
            if not pinecone_result.get("success", False):
                raise Exception(f"Pinecone search failed: {pinecone_result.get('error', 'Unknown error')}")
            
            search_results = pinecone_result.get("matches", [])
            logger.info(f"✅ Pinecone search successful: {len(search_results)} results")
            
            # Step 2: Get additional context from DynamoDB via MCP Server
            logger.info("💾 Getting additional context from DynamoDB MCP Server")
            dynamodb_context = []
            
            for match in search_results[:5]:  # Top 5 results
                chunk_id = match.get("id", "")
                if chunk_id:
                    # Get chunk details from DynamoDB
                    dynamodb_result = await mcp_client.dynamodb_get_item(
                        table_name="document-chunks",
                        key={"chunk_id": chunk_id}
                    )
                    
                    if dynamodb_result.get("success", False):
                        item = dynamodb_result.get("item", {})
                        dynamodb_context.append({
                            "chunk_id": chunk_id,
                            "text": item.get("text", ""),
                            "document_id": item.get("document_id", ""),
                            "metadata": item.get("metadata", {}),
                            "similarity_score": match.get("score", 0)
                        })
            
            logger.info(f"✅ DynamoDB context retrieved: {len(dynamodb_context)} chunks")
            
            # Step 3: Graph queries with Neo4j MCP Server
            logger.info("🕸️ Performing graph queries with Neo4j MCP Server")
            
            # Find related documents and concepts
            graph_cypher = """
            MATCH (c:Chunk)-[:CONTAINS]-(d:Document)
            WHERE c.text CONTAINS $query OR d.filename CONTAINS $query
            RETURN d.filename as document, c.text as chunk_text, c.chunk_index as chunk_index
            ORDER BY c.chunk_index
            LIMIT 10
            """
            
            neo4j_result = await mcp_client.neo4j_execute_query(
                cypher=graph_cypher,
                parameters={"query": query}
            )
            
            graph_context = []
            if neo4j_result.get("success", False):
                graph_context = neo4j_result.get("results", [])
                logger.info(f"✅ Neo4j graph query successful: {len(graph_context)} results")
            else:
                logger.warning(f"Neo4j graph query failed: {neo4j_result.get('error', 'Unknown error')}")
            
            # Step 4: Prepare context for OpenAI
            logger.info("🤖 Preparing context for OpenAI response generation")
            
            # Combine all context sources
            combined_context = {
                "vector_search_results": search_results,
                "dynamodb_chunks": dynamodb_context,
                "graph_relations": graph_context,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create context summary for OpenAI
            context_text = f"""
Query: {query}

Relevant Documents and Chunks:
"""
            
            for i, chunk in enumerate(dynamodb_context[:5]):
                context_text += f"""
{i+1}. Document: {chunk.get('document_id', 'Unknown')}
   Chunk: {chunk.get('text', '')[:200]}...
   Similarity: {chunk.get('similarity_score', 0):.3f}
"""
            
            if graph_context:
                context_text += "\n\nRelated Graph Information:\n"
                for i, relation in enumerate(graph_context[:3]):
                    context_text += f"""
{i+1}. Document: {relation.get('document', 'Unknown')}
   Chunk: {relation.get('chunk_text', '')[:200]}...
"""
            
            # Step 5: Generate response with OpenAI (via MCP if available, or direct call)
            logger.info("🤖 Generating response with OpenAI")
            
            # For now, we'll return the context. In a full implementation,
            # you would call OpenAI MCP server or OpenAI API directly
            response = {
                "query": query,
                "response": f"Based on the knowledge base, I found {len(dynamodb_context)} relevant chunks and {len(graph_context)} related graph connections. Here's what I found:\n\n{context_text}",
                "sources": [
                    {
                        "document_id": chunk.get("document_id"),
                        "chunk_id": chunk.get("chunk_id"),
                        "similarity_score": chunk.get("similarity_score"),
                        "text_preview": chunk.get("text", "")[:100] + "..."
                    }
                    for chunk in dynamodb_context[:5]
                ],
                "graph_relations": graph_context[:3],
                "total_results": len(search_results),
                "processing_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Chat query processing completed successfully")
            
            return {
                "success": True,
                "response": response,
                "query": query,
                "user_id": user_id,
                "results_count": len(search_results),
                "context_chunks": len(dynamodb_context),
                "graph_relations": len(graph_context)
            }
            
    except Exception as e:
        logger.error(f"❌ Chat query processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "user_id": user_id
        }

def lambda_handler(event, context):
    """
    AWS Lambda handler for chat orchestration
    """
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== CHAT ORCHESTRATOR BUSINESS LOGIC STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event: {json.dumps(event, default=str)}")
    
    try:
        # Parse the incoming request
        if isinstance(event, str):
            event = json.loads(event)
        
        # Extract query and user information
        query = event.get("query", "")
        user_id = event.get("user_id", "anonymous")
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "Query parameter is required",
                    "request_id": request_id
                })
            }
        
        logger.info(f"💬 Processing chat query from user {user_id}: {query[:100]}...")
        
        # Process query with MCP servers
        result = asyncio.run(process_chat_query_with_mcp(query, user_id))
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 Total processing time: {processing_time:.3f}s")
        
        # Add processing time to result
        if isinstance(result, dict):
            result["processing_time"] = processing_time
            result["request_id"] = request_id
        
        return {
            "statusCode": 200 if result["success"] else 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps(result)
        }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Lambda handler error: {e}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "request_id": request_id
            })
        }
