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

from agents import function_tool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig
logger.info("✅ Imported agents modules: function_tool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig")

from openai.types.shared.reasoning import Reasoning
logger.info("✅ Imported openai.types.shared.reasoning.Reasoning")

from pydantic import BaseModel, Field
logger.info("✅ Imported pydantic.BaseModel, Field")

from typing import List, Dict, Any, Optional, Union
logger.info("✅ Imported typing.List, Dict, Any, Optional")

import time
logger.info("✅ Imported time module")

import asyncio
logger.info("✅ Imported asyncio module")

from datetime import datetime
logger.info("✅ Imported datetime module")

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
# PYDANTIC MODELS FOR FUNCTION TOOLS (Pydantic 2.x Compatible)
# ============================================================================

class GenericResponse(BaseModel):
    """Generic response model for function tools"""
    success: bool = Field(description="Whether the operation was successful")
    data: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if any")
    message: Optional[str] = Field(default=None, description="Additional message")

class SearchPineconeRequest(BaseModel):
    """Request model for Pinecone search"""
    query_vector: List[float] = Field(description="Query vector for search")
    limit: int = Field(default=10, description="Maximum number of results")

class SearchNeo4jRequest(BaseModel):
    """Request model for Neo4j search"""
    cypher_query: str = Field(description="Cypher query to execute")
    parameters: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Query parameters")

class DynamoDBKeyRequest(BaseModel):
    """Request model for DynamoDB operations with key"""
    table_name: str = Field(description="DynamoDB table name")
    key: Dict[str, Union[str, int, float, bool]] = Field(description="Item key")

class DynamoDBWriteRequest(BaseModel):
    """Request model for DynamoDB write operations"""
    table_name: str = Field(description="DynamoDB table name")
    item: Dict[str, Union[str, int, float, bool]] = Field(description="Item to write")

class DynamoDBUpdateRequest(BaseModel):
    """Request model for DynamoDB update operations"""
    table_name: str = Field(description="DynamoDB table name")
    key: Dict[str, Union[str, int, float, bool]] = Field(description="Item key")
    update_expression: str = Field(description="Update expression")
    expression_values: Dict[str, Union[str, int, float, bool]] = Field(description="Expression values")

class EmbeddingRequest(BaseModel):
    """Request model for embedding generation"""
    text: str = Field(description="Text to generate embedding for")

class PineconeUpsertRequest(BaseModel):
    """Request model for Pinecone upsert operations"""
    vectors: List[Dict[str, Union[str, int, float, bool]]] = Field(description="Vectors to upsert")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace")

class PineconeDeleteRequest(BaseModel):
    """Request model for Pinecone delete operations"""
    ids: List[str] = Field(description="Vector IDs to delete")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace")

class Neo4jWriteRequest(BaseModel):
    """Request model for Neo4j write operations"""
    cypher_query: str = Field(description="Cypher query to execute")
    parameters: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Query parameters")

class QueryDecompositionRequest(BaseModel):
    """Request model for query decomposition"""
    user_query: str = Field(description="User query to decompose")

class RAGSearchRequest(BaseModel):
    """Request model for RAG search"""
    query: str = Field(description="Search query")
    limit: int = Field(default=5, description="Maximum number of results")
    filter_dict: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Filter criteria")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace")

class DocumentUpsertRequest(BaseModel):
    """Request model for document upsert"""
    document_id: str = Field(description="Document ID")
    chunks: List[Dict[str, Union[str, int, float, bool]]] = Field(description="Document chunks")
    metadata: Dict[str, Union[str, int, float, bool]] = Field(description="Document metadata")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace")

class DocumentChunkRequest(BaseModel):
    """Request model for document chunking"""
    document_text: str = Field(description="Document text to chunk")
    chunk_size: int = Field(default=1000, description="Chunk size")
    chunk_overlap: int = Field(default=200, description="Chunk overlap")

class DocumentProcessingRequest(BaseModel):
    """Request model for document processing"""
    document_path: str = Field(description="Path to document")
    document_id: Optional[str] = Field(default=None, description="Document ID")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace")

class DocumentBytesProcessingRequest(BaseModel):
    """Request model for document processing from bytes"""
    document_bytes: bytes = Field(description="Document content as bytes")
    filename: str = Field(description="Original filename")
    document_id: Optional[str] = Field(default=None, description="Document ID")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace")

# ============================================================================
# CRUD TOOLS ONLY - NO BUSINESS LOGIC
# ============================================================================

@function_tool
def read_s3_data_tool(bucket: str, key: str) -> GenericResponse:
    """CRUD: Read data from S3 bucket"""
    result = read_s3_data_crud(bucket, key)
    return GenericResponse(success=True, data=result)

@function_tool
def search_pinecone_tool(request: SearchPineconeRequest) -> GenericResponse:
    """CRUD: Search Pinecone vector database"""
    result = search_pinecone_crud(request.query_vector, request.limit)
    return GenericResponse(success=True, data=result)

@function_tool
def search_neo4j_tool(request: SearchNeo4jRequest) -> GenericResponse:
    """CRUD: Execute Cypher query in Neo4j"""
    result = search_neo4j_crud(request.cypher_query, request.parameters)
    return GenericResponse(success=True, data=result)

@function_tool
def read_dynamodb_tool(request: DynamoDBKeyRequest) -> GenericResponse:
    """CRUD: Read item from DynamoDB table"""
    result = read_dynamodb_crud(request.table_name, request.key)
    return GenericResponse(success=True, data=result)

@function_tool
def batch_read_dynamodb_tool(table_name: str, keys: List[Dict[str, Any]]) -> GenericResponse:
    """CRUD: Batch read items from DynamoDB table"""
    result = batch_read_dynamodb_crud(table_name, keys)
    return GenericResponse(success=True, data=result)

@function_tool
def write_dynamodb_tool(request: DynamoDBWriteRequest) -> GenericResponse:
    """CRUD: Write item to DynamoDB table"""
    result = write_dynamodb_crud(request.table_name, request.item)
    return GenericResponse(success=True, data=result)

@function_tool
def update_dynamodb_tool(request: DynamoDBUpdateRequest) -> GenericResponse:
    """CRUD: Update item in DynamoDB table"""
    result = update_dynamodb_crud(request.table_name, request.key, request.update_expression, request.expression_values)
    return GenericResponse(success=True, data=result)

@function_tool
def delete_dynamodb_tool(request: DynamoDBKeyRequest) -> GenericResponse:
    """CRUD: Delete item from DynamoDB table"""
    result = delete_dynamodb_crud(request.table_name, request.key)
    return GenericResponse(success=True, data=result)

@function_tool
def generate_embedding_tool(request: EmbeddingRequest) -> GenericResponse:
    """CRUD: Generate embedding vector for text"""
    result = generate_embedding_crud(request.text)
    return GenericResponse(success=True, data=result)

@function_tool
def upsert_pinecone_tool(request: PineconeUpsertRequest) -> GenericResponse:
    """CRUD: Upsert vectors to Pinecone"""
    result = upsert_pinecone_crud(request.vectors, request.namespace)
    return GenericResponse(success=True, data=result)

@function_tool
def delete_pinecone_tool(request: PineconeDeleteRequest) -> GenericResponse:
    """CRUD: Delete vectors from Pinecone"""
    result = delete_pinecone_crud(request.ids, request.namespace)
    return GenericResponse(success=True, data=result)

@function_tool
def execute_neo4j_write_tool(request: Neo4jWriteRequest) -> GenericResponse:
    """CRUD: Execute write Cypher query in Neo4j"""
    result = execute_neo4j_write_crud(request.cypher_query, request.parameters)
    return GenericResponse(success=True, data=result)

# ============================================================================
# QUERY DECOMPOSITION TOOLS
# ============================================================================

@function_tool
def decompose_query_tool(request: QueryDecompositionRequest) -> GenericResponse:
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

        User Query: "{request.user_query}"

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
                        "question": request.user_query,
                        "question_type": "factual",
                        "priority": 1,
                        "context": "Original query"
                    }
                ],
                "original_query": request.user_query,
                "decomposition_notes": "Could not parse decomposition, treating as single question"
            }
        
        return GenericResponse(success=True, data={
            "decomposition": decomposition_data,
            "sub_question_count": len(decomposition_data.get("sub_questions", [])),
            "is_multi_part": decomposition_data.get("is_multi_part", False)
        })
        
    except Exception as e:
        return GenericResponse(success=False, error=str(e), data={
            "decomposition": {
                "is_multi_part": False,
                "sub_questions": [{"question": request.user_query, "question_type": "factual", "priority": 1, "context": "Original query"}],
                "original_query": request.user_query,
                "decomposition_notes": f"Error in decomposition: {str(e)}"
            }
        })

# ============================================================================
# PRODUCTION RAG TOOLS
# ============================================================================

@function_tool
def rag_search_tool(request: RAGSearchRequest) -> GenericResponse:
    """RAG: Complete search pipeline with Pinecone + Neo4j + DynamoDB"""
    result = rag_search_crud(request.query, request.limit, request.filter_dict, request.namespace)
    return GenericResponse(success=True, data=result)

@function_tool
def rag_upsert_document_tool(request: DocumentUpsertRequest) -> GenericResponse:
    """RAG: Complete document ingestion pipeline"""
    result = rag_upsert_document_crud(request.document_id, request.chunks, request.metadata, request.namespace)
    return GenericResponse(success=True, data=result)

@function_tool
def rag_chunk_document_tool(request: DocumentChunkRequest) -> GenericResponse:
    """RAG: Chunk document text for processing"""
    result = rag_chunk_document_crud(request.document_text, request.chunk_size, request.chunk_overlap)
    return GenericResponse(success=True, data={"chunks": result})

@function_tool
def rag_process_document_with_docling_tool(request: DocumentProcessingRequest) -> GenericResponse:
    """RAG: Process document using Docling with hierarchical semantic chunking"""
    result = rag_process_document_with_docling_crud(request.document_path, request.document_id, request.namespace)
    return GenericResponse(success=True, data=result)

@function_tool
def rag_process_document_from_bytes_tool(request: DocumentBytesProcessingRequest) -> GenericResponse:
    """RAG: Process document from bytes using Docling (useful for S3 documents)"""
    result = rag_process_document_from_bytes_crud(request.document_bytes, request.filename, request.document_id, request.namespace)
    return GenericResponse(success=True, data=result)

@function_tool
def rag_search_with_hierarchical_context_tool(request: RAGSearchRequest) -> GenericResponse:
    """RAG: Enhanced RAG search with hierarchical context from Docling chunks"""
    result = rag_search_with_hierarchical_context_crud(request.query, request.limit, request.filter_dict, request.namespace)
    return GenericResponse(success=True, data=result)

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
    model="gpt-4",
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
        # Production RAG tools
        rag_search_tool,
        rag_upsert_document_tool,
        rag_chunk_document_tool,
        # Docling-powered RAG tools
        rag_process_document_with_docling_tool,
        rag_process_document_from_bytes_tool,
        rag_search_with_hierarchical_context_tool
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
