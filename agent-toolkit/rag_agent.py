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

from agents import Agent, Runner, function_tool
logger.info("✅ Imported openai-agents modules: Agent, Runner, function_tool")

from pydantic import BaseModel
logger.info("✅ Imported pydantic.BaseModel")

from typing import List, Dict, Any, Optional
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

@function_tool
def read_s3_data_tool(bucket: str, key: str) -> Dict[str, Any]:
    """CRUD: Read data from S3 bucket"""
    return read_s3_data_crud(bucket, key)

@function_tool
def search_pinecone_tool(query_vector: List[float], limit: int = 10) -> str:
    """CRUD: Search Pinecone vector database"""
    result = search_pinecone_crud(query_vector, limit)
    return str(result)

@function_tool
def search_neo4j_tool(cypher_query: str) -> str:
    """CRUD: Execute Cypher query in Neo4j"""
    result = search_neo4j_crud(cypher_query, None)
    return str(result)

@function_tool
def read_dynamodb_tool(table_name: str, key: str) -> str:
    """CRUD: Read item from DynamoDB table"""
    result = read_dynamodb_crud(table_name, eval(key))
    return str(result)

@function_tool
def batch_read_dynamodb_tool(table_name: str, keys: str) -> str:
    """CRUD: Batch read items from DynamoDB table"""
    result = batch_read_dynamodb_crud(table_name, eval(keys))
    return str(result)

@function_tool
def write_dynamodb_tool(table_name: str, item: str) -> str:
    """CRUD: Write item to DynamoDB table"""
    result = write_dynamodb_crud(table_name, eval(item))
    return str(result)

@function_tool
def update_dynamodb_tool(table_name: str, key: str, update_expression: str, expression_values: str) -> str:
    """CRUD: Update item in DynamoDB table"""
    result = update_dynamodb_crud(table_name, eval(key), update_expression, eval(expression_values))
    return str(result)

@function_tool
def delete_dynamodb_tool(table_name: str, key: str) -> str:
    """CRUD: Delete item from DynamoDB table"""
    result = delete_dynamodb_crud(table_name, eval(key))
    return str(result)

@function_tool
def generate_embedding_tool(text: str) -> str:
    """CRUD: Generate embedding vector for text"""
    result = generate_embedding_crud(text)
    return str(result)

@function_tool
def upsert_pinecone_tool(vectors: str, namespace: str = "") -> str:
    """CRUD: Upsert vectors to Pinecone"""
    result = upsert_pinecone_crud(eval(vectors), namespace if namespace else None)
    return str(result)

@function_tool
def delete_pinecone_tool(ids: str, namespace: str = "") -> str:
    """CRUD: Delete vectors from Pinecone"""
    result = delete_pinecone_crud(eval(ids), namespace if namespace else None)
    return str(result)

@function_tool
def execute_neo4j_write_tool(cypher_query: str) -> str:
    """CRUD: Execute write Cypher query in Neo4j"""
    result = execute_neo4j_write_crud(cypher_query, None)
    return str(result)

# ============================================================================
# QUERY DECOMPOSITION TOOLS
# ============================================================================

@function_tool
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

@function_tool
def rag_search_tool(query: str, limit: int = 5, filter_dict: str = "", namespace: str = "") -> str:
    """RAG: Complete search pipeline with Pinecone + Neo4j + DynamoDB"""
    result = rag_search_crud(query, limit, eval(filter_dict) if filter_dict else None, namespace if namespace else None)
    return str(result)

@function_tool
def rag_upsert_document_tool(document_id: str, chunks: str, metadata: str, namespace: str = "") -> str:
    """RAG: Complete document ingestion pipeline"""
    result = rag_upsert_document_crud(document_id, eval(chunks), eval(metadata), namespace if namespace else None)
    return str(result)

@function_tool
def rag_chunk_document_tool(document_text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> str:
    """RAG: Intelligent text chunking"""
    result = rag_chunk_document_crud(document_text, chunk_size, chunk_overlap)
    return str(result)

@function_tool
def rag_process_document_with_docling_tool(document_path: str, document_id: str = "", namespace: str = "") -> str:
    """RAG: Advanced document processing with hierarchical semantic chunking"""
    result = rag_process_document_with_docling_crud(document_path, document_id if document_id else None, namespace if namespace else None)
    return str(result)

@function_tool
def rag_process_document_from_bytes_tool(document_bytes: bytes, filename: str, document_id: str = "", namespace: str = "") -> str:
    """RAG: Process document from bytes using Docling (useful for S3 documents)"""
    result = rag_process_document_from_bytes_crud(document_bytes, filename, document_id if document_id else None, namespace if namespace else None)
    return str(result)

@function_tool
def rag_search_with_hierarchical_context_tool(query: str, limit: int = 5, filter_dict: str = "", namespace: str = "") -> str:
    """RAG: Enhanced RAG search with hierarchical context from Docling chunks"""
    result = rag_search_with_hierarchical_context_crud(query, limit, eval(filter_dict) if filter_dict else None, namespace if namespace else None)
    return str(result)

# ============================================================================
# RAG AGENT - PRODUCTION RAG PIPELINE
# ============================================================================

# Create the unified CRUD agent using openai-agents
rag_agent = Agent(
    name="RAG Agent",
    instructions="""You are a RAG Agent that handles intelligent document retrieval and generation using production RAG tools.

## Core Mission:
You provide intelligent responses by searching through documents using vector similarity, knowledge graphs, and metadata.

## Available RAG Tools:
- **RAG Search**: rag_search_tool - Complete search pipeline with Pinecone + Neo4j + DynamoDB
- **RAG Document Processing**: rag_upsert_document_tool - Complete document ingestion pipeline
- **RAG Text Chunking**: rag_chunk_document_tool - Intelligent text chunking
- **Docling Document Processing**: rag_process_document_with_docling_tool - Advanced document processing with hierarchical semantic chunking
- **Docling Bytes Processing**: rag_process_document_from_bytes_tool - Process documents from bytes (S3 compatible)
- **Hierarchical RAG Search**: rag_search_with_hierarchical_context_tool - Enhanced search with document structure context
- **Individual CRUD Tools**: All individual database operations for fine-grained control

## Your Responsibilities:
1. **Query Decomposition**: Use decompose_query_tool to break complex queries into sub-questions
2. **Query Understanding**: Analyze user queries to determine search strategy
3. **RAG Search**: Use rag_search_tool for comprehensive document retrieval
4. **Context Processing**: Analyze retrieved documents and relationships
5. **Response Generation**: Create intelligent responses based on retrieved context
6. **Document Processing**: Use rag_upsert_document_tool for new document ingestion

## Key Principles:
- **CRUD Tools Only**: Use tools only for Create, Read, Update, Delete operations
- **AI Business Logic**: All decision-making, processing, and formatting handled by you
- **Natural Intelligence**: Use your language understanding for everything
- **Context Awareness**: Understand and respond to user needs intelligently

## Workflow for Knowledge Retrieval:
1. **Decompose Query**: Use decompose_query_tool to break complex queries into sub-questions
2. **Understand Query**: Use your AI to analyze what the user wants
3. **Generate Embedding**: Use generate_embedding_tool to create query vector
4. **Search Pinecone**: Use search_pinecone_tool to find similar vectors
5. **Search Neo4j**: Use search_neo4j_tool with intelligent Cypher queries
6. **Get Details**: Use batch_read_dynamodb_tool to get chunk details
7. **Process Results**: Use your AI to analyze and synthesize information
8. **Generate Response**: Use your AI to create natural, helpful responses

## Multi-Part Query Handling:
When you receive a complex query that contains multiple questions:
1. **First**: Use decompose_query_tool to break it into individual sub-questions
2. **Then**: For each sub-question, use rag_search_tool to find relevant information
3. **Finally**: Structure your response to address each sub-question clearly:
   - Use numbered sections or bullet points
   - Provide specific answers for each question
   - Maintain logical flow and connections between answers
   - If questions are related, explain the connections

## Response Structure for Multi-Part Queries:
```
**Answer 1: [First Question]**
[Detailed answer with sources]

**Answer 2: [Second Question]**
[Detailed answer with sources]

**Answer 3: [Third Question]**
[Detailed answer with sources]

**Summary**: [Brief overview connecting all answers]
```

## Workflow for Document Processing:
1. **Read Document**: Use read_s3_data_tool to get document content
2. **Process Content**: Use your AI to understand and structure the document
3. **Generate Embeddings**: Use generate_embedding_tool for content chunks
4. **Store Vectors**: Use upsert_pinecone_tool to store embeddings
5. **Store Metadata**: Use write_dynamodb_tool to store chunk metadata
6. **Create Relationships**: Use execute_neo4j_write_tool to create knowledge graph

## Docling-Powered Document Processing:
For advanced document processing with hierarchical semantic chunking:
1. **Process with Docling**: Use rag_process_document_with_docling_tool for file-based documents
2. **Process from Bytes**: Use rag_process_document_from_bytes_tool for S3/streaming documents
3. **Hierarchical Search**: Use rag_search_with_hierarchical_context_tool for structure-aware search
4. **Document Types**: Docling supports PDF, Word, PowerPoint, HTML, and more
5. **Chunk Types**: Creates title, heading, paragraph, list, table, figure chunks with hierarchy levels
6. **Section Structure**: Maintains document structure with section paths and hierarchy levels
7. **Docling Fallback**: If hierarchical chunking fails, falls back to Docling's default chunking strategy

## Docling Chunk Types and Hierarchy:
- **Title** (Level 0): Document title
- **Heading H1** (Level 1): Main sections
- **Heading H2** (Level 2): Subsections
- **Heading H3+** (Level 3+): Sub-subsections
- **Paragraph** (Level 2): Regular text content
- **List Item** (Level 2): Bullet points and numbered lists
- **Table** (Level 3): Tabular data
- **Figure** (Level 3): Images, charts, diagrams
- **Default Paragraph** (Level 3): Docling's default chunking fallback

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
    model="gpt-4o-mini",
    tools=[
        # Query decomposition tools
        decompose_query_tool,
        
        # Individual CRUD tools
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
        
        # Unified RAG tools
        rag_search_tool,
        rag_upsert_document_tool,
        rag_chunk_document_tool,
        rag_process_document_with_docling_tool,
        rag_process_document_from_bytes_tool,
        rag_search_with_hierarchical_context_tool,
    ]
)

logger.info("✅ Created RAG Agent with all tools using openai-agents")

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
    """Run the unified CRUD processing workflow using openai-agents"""
    start_time = time.time()
    
    try:
        # Create conversation history for the agent
        conversation_history: List[Dict[str, Any]] = [
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
        
        # Add conversation history if provided
        if workflow_input.conversation_history:
            conversation_history.extend(workflow_input.conversation_history)
        
        # Add user preferences context if provided
        if workflow_input.user_preferences:
            conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"User preferences: {workflow_input.user_preferences}"
                    }
                ]
            }
        )
        
        # Run the unified CRUD agent using openai-agents
        crud_result = await Runner.run(
            rag_agent,
            input=workflow_input.user_query
        )

        # Extract the final response
        try:
            final_response = crud_result.final_output
        except Exception as e:
            final_response = f"Error generating response: {str(e)}"
        
        return {
            "response": final_response,
            "sources": [],
            "conversation_id": workflow_input.conversation_id,
            "processing_time": time.time() - start_time,
            "timestamp": datetime.now().isoformat(),
            "model": "gpt-4o-mini",
            "status": "success",
            "workflow_type": "unified_crud_processing",
            "agent_used": "rag_agent",
            "tools_used": "openai-agents",
            "business_logic": "ai_handled"
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
            "error": str(e),
            "workflow_type": "unified_crud_processing",
            "agent_used": "rag_agent"
        }
