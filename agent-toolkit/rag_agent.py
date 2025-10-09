"""
RAG Agent with Production RAG Tools
Complete RAG pipeline with Pinecone, Neo4j, and DynamoDB

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

# Configure logging first
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("✅ Configured logging in rag_agent")

from openai import OpenAI
client = OpenAI()
logger.info("✅ Imported OpenAI client")

from pydantic import BaseModel
logger.info("✅ Imported pydantic.BaseModel")

from typing import List, Dict, Any
logger.info("✅ Imported typing.List, Dict, Any")

import time
logger.info("✅ Imported time module")

import asyncio
logger.info("✅ Imported asyncio module")

import json
logger.info("✅ Imported json module")

# Import CRUD tools and RAG operations
from crud_operations import (
    read_s3_data_crud,
    search_pinecone_crud,
    search_neo4j_crud,
    read_dynamodb_crud,
    batch_read_dynamodb_crud,
    write_dynamodb_crud,
    update_dynamodb_crud,
    delete_dynamodb_crud,
    generate_embedding_crud,
    upsert_pinecone_crud,
    delete_pinecone_crud,
    execute_neo4j_write_crud
)
logger.info("✅ Imported crud_operations modules")

from rag_operations import (
    rag_search_crud,
    rag_upsert_document_crud,
    rag_chunk_document_crud,
    rag_process_document_with_docling_crud,
    rag_process_document_from_bytes_crud,
    rag_search_with_hierarchical_context_crud
)
logger.info("✅ Imported rag_operations modules")

# ============================================================================
# CRUD TOOLS ONLY - NO BUSINESS LOGIC
# ============================================================================

def read_s3_data_tool(bucket: str, key: str) -> Dict[str, Any]:
    """CRUD: Read data from S3 bucket"""
    return read_s3_data_crud(bucket, key)

def search_pinecone_tool(query_vector: List[float], limit: int = 10) -> Dict[str, Any]:
    """CRUD: Search Pinecone vector database"""
    return search_pinecone_crud(query_vector, limit)

def search_neo4j_tool(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """CRUD: Execute Cypher query in Neo4j"""
    return search_neo4j_crud(cypher_query, parameters)

def read_dynamodb_tool(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Read item from DynamoDB table"""
    return read_dynamodb_crud(table_name, key)

def batch_read_dynamodb_tool(table_name: str, keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """CRUD: Batch read items from DynamoDB table"""
    return batch_read_dynamodb_crud(table_name, keys)

def write_dynamodb_tool(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Write item to DynamoDB table"""
    return write_dynamodb_crud(table_name, item)

def update_dynamodb_tool(table_name: str, key: Dict[str, Any], update_expression: str, expression_values: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Update item in DynamoDB table"""
    return update_dynamodb_crud(table_name, key, update_expression, expression_values)

def delete_dynamodb_tool(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Delete item from DynamoDB table"""
    return delete_dynamodb_crud(table_name, key)

def generate_embedding_tool(text: str) -> Dict[str, Any]:
    """CRUD: Generate embedding vector for text"""
    return generate_embedding_crud(text)

def upsert_pinecone_tool(vectors: List[Dict[str, Any]], namespace: str = None) -> Dict[str, Any]:
    """CRUD: Upsert vectors to Pinecone"""
    return upsert_pinecone_crud(vectors, namespace)

def delete_pinecone_tool(ids: List[str], namespace: str = None) -> Dict[str, Any]:
    """CRUD: Delete vectors from Pinecone"""
    return delete_pinecone_crud(ids, namespace)

def execute_neo4j_write_tool(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """CRUD: Execute write Cypher query in Neo4j"""
    return execute_neo4j_write_crud(cypher_query, parameters)

# ============================================================================
# QUERY DECOMPOSITION TOOLS
# ============================================================================

def decompose_query_tool(user_query: str) -> Dict[str, Any]:
    """
    Decompose complex user queries into individual sub-questions
    
    Args:
        user_query: The original user query that may contain multiple questions
        
    Returns:
        Dictionary with decomposed sub-questions and metadata
    """
    try:
        # Use GPT-4 to analyze and decompose the query
        import openai
        
        decomposition_prompt = f"""
        Analyze the following user query and break it down into individual, specific questions if it contains multiple questions or complex requests.

        User Query: "{user_query}"

        Instructions:
        1. If the query contains multiple questions, separate them into individual questions
        2. If the query is complex but single, break it into logical sub-questions
        3. If the query is already simple and single, return it as is
        4. Each sub-question should be self-contained and answerable independently
        5. Maintain the original intent and context

        Return your response as a JSON object with this structure:
        {{
            "is_multi_part": true/false,
            "sub_questions": [
                {{
                    "question": "specific question text",
                    "question_type": "factual|analytical|comparative|procedural",
                    "priority": 1-5,
                    "context": "brief context for this question"
                }}
            ],
            "original_query": "original user query",
            "decomposition_notes": "any notes about the decomposition"
        }}
        """
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at analyzing and decomposing complex user queries into manageable sub-questions."},
                {"role": "user", "content": decomposition_prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        # Parse the response
        decomposition_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        import json
        import re
        
        # Look for JSON in the response
        json_match = re.search(r'\{.*\}', decomposition_text, re.DOTALL)
        if json_match:
            decomposition_data = json.loads(json_match.group())
        else:
            # Fallback: create simple decomposition
            decomposition_data = {
                "is_multi_part": False,
                "sub_questions": [
                    {
                        "question": user_query,
                        "question_type": "factual",
                        "priority": 1,
                        "context": "Original query"
                    }
                ],
                "original_query": user_query,
                "decomposition_notes": "Could not parse decomposition, treating as single question"
            }
        
        return {
            "success": True,
            "decomposition": decomposition_data,
            "sub_question_count": len(decomposition_data.get("sub_questions", [])),
            "is_multi_part": decomposition_data.get("is_multi_part", False)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "decomposition": {
                "is_multi_part": False,
                "sub_questions": [{"question": user_query, "question_type": "factual", "priority": 1, "context": "Original query"}],
                "original_query": user_query,
                "decomposition_notes": f"Error in decomposition: {str(e)}"
            }
        }

# ============================================================================
# PRODUCTION RAG TOOLS
# ============================================================================

def rag_search_tool(query: str, limit: int = 5, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """RAG: Complete search pipeline with Pinecone + Neo4j + DynamoDB"""
    return rag_search_crud(query, limit, filter_dict, namespace)

def rag_upsert_document_tool(document_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any], namespace: str = None) -> Dict[str, Any]:
    """RAG: Complete document ingestion pipeline"""
    return rag_upsert_document_crud(document_id, chunks, metadata, namespace)

def rag_chunk_document_tool(document_text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """RAG: Chunk document text for processing"""
    return rag_chunk_document_crud(document_text, chunk_size, chunk_overlap)

def rag_process_document_with_docling_tool(document_path: str, document_id: str = None, namespace: str = None) -> Dict[str, Any]:
    """RAG: Process document using Docling with hierarchical semantic chunking"""
    return rag_process_document_with_docling_crud(document_path, document_id, namespace)

def rag_process_document_from_bytes_tool(document_bytes: bytes, filename: str, document_id: str = None, namespace: str = None) -> Dict[str, Any]:
    """RAG: Process document from bytes using Docling (useful for S3 documents)"""
    return rag_process_document_from_bytes_crud(document_bytes, filename, document_id, namespace)

def rag_search_with_hierarchical_context_tool(query: str, limit: int = 5, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """RAG: Enhanced RAG search with hierarchical context from Docling chunks"""
    return rag_search_with_hierarchical_context_crud(query, limit, filter_dict, namespace)

# ============================================================================
# RAG AGENT - PRODUCTION RAG PIPELINE
# ============================================================================

# Note: Agent creation removed - using OpenAI chat completions directly

class CRUDAgentInput(BaseModel):
    model_config = {"extra": "forbid"}  # Configure to not allow additional properties
    
    user_query: str
    conversation_history: List[Dict[str, Any]] = []
    conversation_id: str = ""
    user_preferences: Dict[str, Any] = {}

# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

async def run_unified_crud_processing(workflow_input: CRUDAgentInput) -> Dict[str, Any]:
    """Run the unified CRUD processing workflow using OpenAI Function Calling"""
    start_time = time.time()
    
    try:
        # Define all available tools for OpenAI Function Calling
        tools = [
            # Query decomposition tools
            {
                "type": "function",
                "function": {
                    "name": "decompose_query_tool",
                    "description": "Decompose complex user queries into individual sub-questions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_query": {
                                "type": "string",
                                "description": "The original user query that may contain multiple questions"
                            }
                        },
                        "required": ["user_query"]
                    }
                }
            },
            
            # Individual CRUD tools
            {
                "type": "function",
                "function": {
                    "name": "read_s3_data_tool",
                    "description": "CRUD: Read data from S3 bucket",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bucket": {"type": "string", "description": "S3 bucket name"},
                            "key": {"type": "string", "description": "S3 object key"}
                        },
                        "required": ["bucket", "key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_pinecone_tool",
                    "description": "CRUD: Search Pinecone vector database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_vector": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "Query vector for similarity search"
                            },
                            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                        },
                        "required": ["query_vector"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_neo4j_tool",
                    "description": "CRUD: Execute Cypher query in Neo4j",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cypher_query": {"type": "string", "description": "Cypher query to execute"},
                            "parameters": {"type": "object", "description": "Query parameters", "default": {}}
                        },
                        "required": ["cypher_query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_dynamodb_tool",
                    "description": "CRUD: Read item from DynamoDB table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "DynamoDB table name"},
                            "key": {"type": "object", "description": "Primary key for the item"}
                        },
                        "required": ["table_name", "key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "batch_read_dynamodb_tool",
                    "description": "CRUD: Batch read items from DynamoDB table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "DynamoDB table name"},
                            "keys": {"type": "array", "description": "List of primary keys"}
                        },
                        "required": ["table_name", "keys"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_dynamodb_tool",
                    "description": "CRUD: Write item to DynamoDB table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "DynamoDB table name"},
                            "item": {"type": "object", "description": "Item to write"}
                        },
                        "required": ["table_name", "item"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_dynamodb_tool",
                    "description": "CRUD: Update item in DynamoDB table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "DynamoDB table name"},
                            "key": {"type": "object", "description": "Primary key for the item"},
                            "update_expression": {"type": "string", "description": "Update expression"},
                            "expression_values": {"type": "object", "description": "Expression attribute values"}
                        },
                        "required": ["table_name", "key", "update_expression", "expression_values"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_dynamodb_tool",
                    "description": "CRUD: Delete item from DynamoDB table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "DynamoDB table name"},
                            "key": {"type": "object", "description": "Primary key for the item"}
                        },
                        "required": ["table_name", "key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_embedding_tool",
                    "description": "CRUD: Generate embedding vector for text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to generate embedding for"}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "upsert_pinecone_tool",
                    "description": "CRUD: Upsert vectors to Pinecone",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vectors": {"type": "array", "description": "List of vectors to upsert"},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["vectors"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_pinecone_tool",
                    "description": "CRUD: Delete vectors from Pinecone",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ids": {"type": "array", "items": {"type": "string"}, "description": "Vector IDs to delete"},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_neo4j_write_tool",
                    "description": "CRUD: Execute write Cypher query in Neo4j",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cypher_query": {"type": "string", "description": "Cypher query to execute"},
                            "parameters": {"type": "object", "description": "Query parameters", "default": {}}
                        },
                        "required": ["cypher_query"]
                    }
                }
            },
            
            # Unified RAG tools
            {
                "type": "function",
                "function": {
                    "name": "rag_search_tool",
                    "description": "RAG: Complete search pipeline with Pinecone + Neo4j + DynamoDB",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "description": "Maximum number of results", "default": 5},
                            "filter_dict": {"type": "object", "description": "Filter criteria", "default": None},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_upsert_document_tool",
                    "description": "RAG: Complete document ingestion pipeline",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_content": {"type": "string", "description": "Document content to process"},
                            "document_id": {"type": "string", "description": "Unique document identifier"},
                            "filename": {"type": "string", "description": "Original filename"},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["document_content", "document_id", "filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_chunk_document_tool",
                    "description": "RAG: Intelligent text chunking",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to chunk"},
                            "chunk_size": {"type": "integer", "description": "Maximum chunk size", "default": 1000},
                            "chunk_overlap": {"type": "integer", "description": "Overlap between chunks", "default": 200}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_process_document_with_docling_tool",
                    "description": "RAG: Advanced document processing with hierarchical semantic chunking",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Path to document file"},
                            "document_id": {"type": "string", "description": "Unique document identifier"},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["file_path", "document_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_process_document_from_bytes_tool",
                    "description": "RAG: Process document from bytes using Docling (useful for S3 documents)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_bytes": {"type": "string", "description": "Document bytes (base64 encoded)"},
                            "filename": {"type": "string", "description": "Original filename"},
                            "document_id": {"type": "string", "description": "Unique document identifier"},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["document_bytes", "filename", "document_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_search_with_hierarchical_context_tool",
                    "description": "RAG: Enhanced RAG search with hierarchical context from Docling chunks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "description": "Maximum number of results", "default": 5},
                            "filter_dict": {"type": "object", "description": "Filter criteria", "default": None},
                            "namespace": {"type": "string", "description": "Pinecone namespace", "default": None}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        # Create system message with instructions
        system_message = """You are a RAG Agent that handles intelligent document retrieval and generation using production RAG tools.

## Core Mission:
You provide intelligent responses by searching through documents using vector similarity, knowledge graphs, and metadata.

## Available Tools:
You have access to comprehensive RAG tools including:
- **Query Decomposition**: decompose_query_tool - Break complex queries into sub-questions
- **Individual CRUD Tools**: All database operations (S3, DynamoDB, Pinecone, Neo4j)
- **Unified RAG Tools**: Complete pipelines for search and document processing
- **Docling Tools**: Advanced document processing with hierarchical chunking

## Your Workflow:
1. **Analyze the Query**: Understand what the user is asking for
2. **Decompose if Needed**: Use decompose_query_tool for complex multi-part queries
3. **Execute RAG Search**: Use rag_search_tool for comprehensive document retrieval
4. **Process Results**: Analyze retrieved information and relationships
5. **Generate Response**: Create intelligent, helpful responses with source attribution

## Key Principles:
- **Use Tools Actively**: Call the appropriate tools to gather information
- **Provide Sources**: Always cite where information came from
- **Handle Multi-Part Queries**: Break down complex questions systematically
- **Be Comprehensive**: Use multiple tools when needed for complete answers

## Multi-Part Query Handling:
When you receive a complex query with multiple questions:
1. Use decompose_query_tool to break it into sub-questions
2. For each sub-question, use rag_search_tool to find relevant information
3. Structure your response to address each question clearly
4. Provide a summary connecting all answers

Always use the available tools to provide accurate, well-sourced responses."""

        # Initialize conversation
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": workflow_input.user_query}
        ]

        # Add conversation history if provided
        if workflow_input.conversation_history:
            messages.extend(workflow_input.conversation_history)

        # Add user preferences context if provided
        if workflow_input.user_preferences:
            messages.append({
                "role": "user",
                "content": f"User preferences: {workflow_input.user_preferences}"
            })

        # Execute conversation with function calling
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call OpenAI with function calling enabled
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=4096
            )
            
            message = response.choices[0].message
            messages.append(message)
            
            # Check if the model wants to call a function
            if message.tool_calls:
                # Execute each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)  # Parse JSON arguments
                    
                    logger.info(f"Executing tool: {function_name} with args: {function_args}")
                    
                    try:
                        # Execute the function
                        if function_name == "decompose_query_tool":
                            result = decompose_query_tool(**function_args)
                        elif function_name == "read_s3_data_tool":
                            result = read_s3_data_tool(**function_args)
                        elif function_name == "search_pinecone_tool":
                            result = search_pinecone_tool(**function_args)
                        elif function_name == "search_neo4j_tool":
                            result = search_neo4j_tool(**function_args)
                        elif function_name == "read_dynamodb_tool":
                            result = read_dynamodb_tool(**function_args)
                        elif function_name == "batch_read_dynamodb_tool":
                            result = batch_read_dynamodb_tool(**function_args)
                        elif function_name == "write_dynamodb_tool":
                            result = write_dynamodb_tool(**function_args)
                        elif function_name == "update_dynamodb_tool":
                            result = update_dynamodb_tool(**function_args)
                        elif function_name == "delete_dynamodb_tool":
                            result = delete_dynamodb_tool(**function_args)
                        elif function_name == "generate_embedding_tool":
                            result = generate_embedding_tool(**function_args)
                        elif function_name == "upsert_pinecone_tool":
                            result = upsert_pinecone_tool(**function_args)
                        elif function_name == "delete_pinecone_tool":
                            result = delete_pinecone_tool(**function_args)
                        elif function_name == "execute_neo4j_write_tool":
                            result = execute_neo4j_write_tool(**function_args)
                        elif function_name == "rag_search_tool":
                            result = rag_search_tool(**function_args)
                        elif function_name == "rag_upsert_document_tool":
                            result = rag_upsert_document_tool(**function_args)
                        elif function_name == "rag_chunk_document_tool":
                            result = rag_chunk_document_tool(**function_args)
                        elif function_name == "rag_process_document_with_docling_tool":
                            result = rag_process_document_with_docling_tool(**function_args)
                        elif function_name == "rag_process_document_from_bytes_tool":
                            result = rag_process_document_from_bytes_tool(**function_args)
                        elif function_name == "rag_search_with_hierarchical_context_tool":
                            result = rag_search_with_hierarchical_context_tool(**function_args)
                        else:
                            result = {"error": f"Unknown function: {function_name}"}
                        
                        # Add function result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error executing {function_name}: {str(e)}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {str(e)}"
                        })
            else:
                # No more tool calls, we have the final response
                break
        
        # Extract final response
        final_response = messages[-1]["content"] if messages[-1]["role"] == "assistant" else "No response generated"
        processing_time = time.time() - start_time
        
        return {
            "response": final_response,
            "sources": [],
            "conversation_id": workflow_input.conversation_id,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "model": "gpt-4o-mini",
            "status": "success",
            "iterations": iteration
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error in run_unified_crud_processing: {str(e)}")
        
        return {
            "response": f"Error processing request: {str(e)}",
            "sources": [],
            "conversation_id": workflow_input.conversation_id,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "model": "gpt-4o-mini",
            "status": "error",
            "error": str(e)
        }
