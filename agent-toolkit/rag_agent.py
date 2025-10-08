"""
RAG Agent with Production RAG Tools
Complete RAG pipeline with Pinecone, Neo4j, and DynamoDB
"""

from agents import function_tool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel
from typing import List, Dict, Any
import time
import asyncio
from datetime import datetime

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
from rag_operations import (
    rag_search_crud,
    rag_upsert_document_crud,
    rag_chunk_document_crud
)

# ============================================================================
# CRUD TOOLS ONLY - NO BUSINESS LOGIC
# ============================================================================

@function_tool
def read_s3_data_tool(bucket: str, key: str) -> Dict[str, Any]:
    """CRUD: Read data from S3 bucket"""
    return read_s3_data_crud(bucket, key)

@function_tool
def search_pinecone_tool(query_vector: List[float], limit: int = 10) -> Dict[str, Any]:
    """CRUD: Search Pinecone vector database"""
    return search_pinecone_crud(query_vector, limit)

@function_tool
def search_neo4j_tool(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """CRUD: Execute Cypher query in Neo4j"""
    return search_neo4j_crud(cypher_query, parameters)

@function_tool
def read_dynamodb_tool(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Read item from DynamoDB table"""
    return read_dynamodb_crud(table_name, key)

@function_tool
def batch_read_dynamodb_tool(table_name: str, keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """CRUD: Batch read items from DynamoDB table"""
    return batch_read_dynamodb_crud(table_name, keys)

@function_tool
def write_dynamodb_tool(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Write item to DynamoDB table"""
    return write_dynamodb_crud(table_name, item)

@function_tool
def update_dynamodb_tool(table_name: str, key: Dict[str, Any], update_expression: str, expression_values: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Update item in DynamoDB table"""
    return update_dynamodb_crud(table_name, key, update_expression, expression_values)

@function_tool
def delete_dynamodb_tool(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """CRUD: Delete item from DynamoDB table"""
    return delete_dynamodb_crud(table_name, key)

@function_tool
def generate_embedding_tool(text: str) -> Dict[str, Any]:
    """CRUD: Generate embedding vector for text"""
    return generate_embedding_crud(text)

@function_tool
def upsert_pinecone_tool(vectors: List[Dict[str, Any]], namespace: str = None) -> Dict[str, Any]:
    """CRUD: Upsert vectors to Pinecone"""
    return upsert_pinecone_crud(vectors, namespace)

@function_tool
def delete_pinecone_tool(ids: List[str], namespace: str = None) -> Dict[str, Any]:
    """CRUD: Delete vectors from Pinecone"""
    return delete_pinecone_crud(ids, namespace)

@function_tool
def execute_neo4j_write_tool(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """CRUD: Execute write Cypher query in Neo4j"""
    return execute_neo4j_write_crud(cypher_query, parameters)

# ============================================================================
# PRODUCTION RAG TOOLS
# ============================================================================

@function_tool
def rag_search_tool(query: str, limit: int = 5, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """RAG: Complete search pipeline with Pinecone + Neo4j + DynamoDB"""
    return rag_search_crud(query, limit, filter_dict, namespace)

@function_tool
def rag_upsert_document_tool(document_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any], namespace: str = None) -> Dict[str, Any]:
    """RAG: Complete document ingestion pipeline"""
    return rag_upsert_document_crud(document_id, chunks, metadata, namespace)

@function_tool
def rag_chunk_document_tool(document_text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """RAG: Chunk document text for processing"""
    return rag_chunk_document_crud(document_text, chunk_size, chunk_overlap)

# ============================================================================
# RAG AGENT - PRODUCTION RAG PIPELINE
# ============================================================================

rag_agent = Agent(
    name="RAG Agent",
    instructions="""You are a RAG Agent that handles intelligent document retrieval and generation using production RAG tools.

## Core Mission:
You provide intelligent responses by searching through documents using vector similarity, knowledge graphs, and metadata.

## Available RAG Tools:
- **RAG Search**: rag_search_tool - Complete search pipeline with Pinecone + Neo4j + DynamoDB
- **RAG Document Processing**: rag_upsert_document_tool - Complete document ingestion pipeline
- **RAG Text Chunking**: rag_chunk_document_tool - Intelligent text chunking
- **Individual CRUD Tools**: All individual database operations for fine-grained control

## Your Responsibilities:
1. **Query Understanding**: Analyze user queries to determine search strategy
2. **RAG Search**: Use rag_search_tool for comprehensive document retrieval
3. **Context Processing**: Analyze retrieved documents and relationships
4. **Response Generation**: Create intelligent responses based on retrieved context
5. **Document Processing**: Use rag_upsert_document_tool for new document ingestion

## Key Principles:
- **CRUD Tools Only**: Use tools only for Create, Read, Update, Delete operations
- **AI Business Logic**: All decision-making, processing, and formatting handled by you
- **Natural Intelligence**: Use your language understanding for everything
- **Context Awareness**: Understand and respond to user needs intelligently

## Workflow for Knowledge Retrieval:
1. **Understand Query**: Use your AI to analyze what the user wants
2. **Generate Embedding**: Use generate_embedding_tool to create query vector
3. **Search Pinecone**: Use search_pinecone_tool to find similar vectors
4. **Search Neo4j**: Use search_neo4j_tool with intelligent Cypher queries
5. **Get Details**: Use batch_read_dynamodb_tool to get chunk details
6. **Process Results**: Use your AI to analyze and synthesize information
7. **Generate Response**: Use your AI to create natural, helpful responses

## Workflow for Document Processing:
1. **Read Document**: Use read_s3_data_tool to get document content
2. **Process Content**: Use your AI to understand and structure the document
3. **Generate Embeddings**: Use generate_embedding_tool for content chunks
4. **Store Vectors**: Use upsert_pinecone_tool to store embeddings
5. **Store Metadata**: Use write_dynamodb_tool to store chunk metadata
6. **Create Relationships**: Use execute_neo4j_write_tool to create knowledge graph

## Response Guidelines:
- Always provide comprehensive, helpful responses
- Use natural language that feels conversational
- Handle multiple questions intelligently
- Provide clear source attribution when using retrieved data
- Adapt your response style to match the user's query complexity
- Handle edge cases gracefully with natural explanations

## Error Handling:
- If CRUD operations fail, use your AI to provide helpful error messages
- Suggest alternative approaches when possible
- Maintain a helpful, professional tone even when errors occur

## Key Principle:
**You are the intelligence** - use your AI capabilities for all business logic, decision-making, processing, and formatting. Tools are only for data operations.

When you receive any query, immediately begin your intelligent analysis and use the appropriate CRUD tools to gather data, then use your AI to process and respond naturally.""",
    model="gpt-4",
    tools=[
        read_s3_data_tool,
        search_pinecone_tool,
        search_neo4j_tool,
        read_dynamodb_tool,
        batch_read_dynamodb_tool,
        write_dynamodb_tool,
        update_dynamodb_tool,
        delete_dynamodb_tool,
        generate_embedding_tool,
        upsert_pinecone_tool,
        delete_pinecone_tool,
        execute_neo4j_write_tool,
        # Production RAG tools
        rag_search_tool,
        rag_upsert_document_tool,
        rag_chunk_document_tool
    ],
    model_settings=ModelSettings(
        temperature=0.1,
        parallel_tool_calls=True,
        max_tokens=4096,
        reasoning=Reasoning(
            effort="high"
        )
    )
)

class CRUDAgentInput(BaseModel):
    user_query: str
    conversation_history: List[Dict[str, Any]] = []
    conversation_id: str = ""
    user_preferences: Dict[str, Any] = {}

# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

async def run_unified_crud_processing(workflow_input: CRUDAgentInput) -> Dict[str, Any]:
    """Run the unified CRUD processing workflow"""
    start_time = time.time()
    
    try:
        # Create conversation history for the agent
        conversation_history: List[TResponseInputItem] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": workflow_input.user_query
                    }
                ]
            }
        ]
        
        # Run the unified CRUD agent
        crud_result = await Runner.run(
            rag_agent,
            input=conversation_history,
            run_config=RunConfig(trace_metadata={
                "__trace_source__": "agent-builder",
                "workflow_id": "unified_crud_processing",
                "conversation_id": workflow_input.conversation_id
            })
        )

        conversation_history.extend([item.to_input_item() for item in crud_result.new_items])

        processing_time = time.time() - start_time
        
        # Extract the final response
        try:
            final_response = crud_result.final_output_as(str)
        except Exception as e:
            final_response = f"Error generating response: {str(e)}"
        
        return {
            "response": final_response,
            "sources": [],
            "conversation_id": workflow_input.conversation_id,
            "processing_time": processing_time,
            "workflow_type": "unified_crud_processing",
            "agent_used": "unified_crud_agent",
            "tools_used": "crud_only",
            "business_logic": "ai_handled"
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        return {
            "response": f"Error processing query: {str(e)}",
            "sources": [],
            "conversation_id": workflow_input.conversation_id,
            "processing_time": processing_time,
            "workflow_type": "unified_crud_processing",
            "agent_used": "unified_crud_agent"
        }
