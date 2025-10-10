#!/usr/bin/env python3
"""
Intelligent Agent Microservice
Central orchestrator that handles all requests, makes decisions, and coordinates microservices
Uses OpenAI Agents framework with comprehensive tool integration
"""

import json
import os
import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import traceback

# Type definitions for better Pydantic compatibility
# Use explicitly structured, fully defined types (not arbitrary/dynamic)
from typing import TypedDict

class VectorData(TypedDict):
    id: str
    values: str  # JSON string of float list
    metadata: str  # JSON string of metadata dict

class DynamoDBKey(TypedDict):
    partition_key: str
    sort_key: str

class DynamoDBItem(TypedDict):
    partition_key: str
    sort_key: str
    data: str  # JSON string of item data

class SearchFilters(TypedDict):
    namespace: str
    metadata_filter: str  # JSON string of metadata filter

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import OpenAI Agents framework
try:
    from openai import Agent, Runner, function_tool
    logger.info("✅ OpenAI Agents framework imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import OpenAI Agents: {e}")
    raise

# Initialize HTTP client for microservice calls
http_client = httpx.AsyncClient(timeout=300.0)

# Microservice URLs (will be set via environment variables)
MICROSERVICE_BASE_URL = os.environ.get('MICROSERVICE_BASE_URL', 'https://api.knowledgebot.com')

async def call_microservice(service_name: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call a microservice endpoint"""
    try:
        url = f"{MICROSERVICE_BASE_URL}/{service_name}/{endpoint}"
        logger.info(f"🔄 Calling {service_name}/{endpoint}")
        
        response = await http_client.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ {service_name}/{endpoint} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error calling {service_name}/{endpoint}: {e}")
        return {"success": False, "error": str(e)}

# ============================================================================
# MICROSERVICE TOOLS
# ============================================================================

@function_tool
async def get_presigned_url_tool(filename: str, content_type: str = "application/pdf") -> str:
    """Get a presigned URL for file upload to S3"""
    result = await call_microservice("presigned-url", "upload", {
        "filename": filename,
        "content_type": content_type
    })
    return json.dumps(result)

@function_tool
async def read_s3_document_tool(s3_url: str) -> str:
    """Read document content from S3"""
    result = await call_microservice("s3-reader", "read", {
        "s3_url": s3_url
    })
    return json.dumps(result)

@function_tool
async def chunk_text_tool(text: str, chunk_size: int = 1000, overlap: int = 200) -> str:
    """Split text into chunks for processing"""
    result = await call_microservice("text-chunker", "chunk", {
        "text": text,
        "chunk_size": chunk_size,
        "overlap": overlap
    })
    return json.dumps(result)

@function_tool
async def generate_embeddings_tool(texts: List[str]) -> str:
    """Generate embeddings for text chunks"""
    result = await call_microservice("embedding-generator", "generate", {
        "texts": texts
    })
    return json.dumps(result)

@function_tool
async def search_pinecone_tool(query_vector: str, limit: int = 10) -> str:
    """Search Pinecone vector database"""
    result = await call_microservice("pinecone-search", "search", {
        "query_vector": query_vector,
        "limit": limit,
        "filters": {}
    })
    return json.dumps(result)

@function_tool
async def upsert_pinecone_tool(vectors: List[VectorData]) -> str:
    """Store vectors in Pinecone"""
    result = await call_microservice("pinecone-upsert", "upsert", {
        "vectors": vectors
    })
    return json.dumps(result)

@function_tool
async def search_neo4j_tool(cypher_query: str) -> str:
    """Search Neo4j graph database"""
    result = await call_microservice("neo4j-search", "search", {
        "cypher_query": cypher_query
    })
    return json.dumps(result)

@function_tool
async def write_neo4j_tool(cypher_query: str) -> str:
    """Write to Neo4j graph database"""
    result = await call_microservice("neo4j-write", "write", {
        "cypher_query": cypher_query
    })
    return json.dumps(result)

@function_tool
async def read_dynamodb_tool(table_name: str, key: DynamoDBKey) -> str:
    """Read from DynamoDB"""
    result = await call_microservice("dynamodb-crud", "read", {
        "table_name": table_name,
        "key": key
    })
    return json.dumps(result)

@function_tool
async def write_dynamodb_tool(table_name: str, item: DynamoDBItem) -> str:
    """Write to DynamoDB"""
    result = await call_microservice("dynamodb-crud", "write", {
        "table_name": table_name,
        "item": item
    })
    return json.dumps(result)

@function_tool
async def rag_search_tool(query: str, limit: int = 5, filters: Optional[SearchFilters] = None) -> str:
    """Perform comprehensive RAG search across all databases"""
    result = await call_microservice("rag-search", "search", {
        "query": query,
        "limit": limit,
        "filters": filters or {}
    })
    return json.dumps(result)

@function_tool
async def process_pdf_tool(document_bytes: str, filename: str) -> str:
    """Process PDF document with advanced extraction"""
    result = await call_microservice("pdf-processor", "process", {
        "document_bytes": document_bytes,
        "filename": filename
    })
    return json.dumps(result)

@function_tool
async def process_ocr_tool(image_data: str, document_type: str = "pdf") -> str:
    """Process OCR on images or scanned documents"""
    result = await call_microservice("easyocr", "process", {
        "image_data": image_data,
        "document_type": document_type
    })
    return json.dumps(result)

@function_tool
async def detect_tables_tool(document_data: str) -> str:
    """Detect and extract tables from documents"""
    result = await call_microservice("table-detector", "detect", {
        "document_data": document_data
    })
    return json.dumps(result)

@function_tool
async def process_docling_core_tool(document_bytes: str, filename: str) -> str:
    """Process document with Docling core functionality"""
    result = await call_microservice("docling-core", "process", {
        "document_bytes": document_bytes,
        "filename": filename
    })
    return json.dumps(result)

@function_tool
async def process_docling_ocr_tool(document_bytes: str, filename: str) -> str:
    """Process document with Docling OCR functionality"""
    result = await call_microservice("docling-ocr", "process", {
        "document_bytes": document_bytes,
        "filename": filename
    })
    return json.dumps(result)

# ============================================================================
# RESPONSE PROCESSING TOOLS
# ============================================================================

@function_tool
def process_final_response_tool(response_text: str, query: str, response_type: str = "comprehensive") -> str:
    """Process and optimize the final response for UI display"""
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        processing_prompt = f"""
        Process the following response for optimal UI display and user experience:

        Original Query: "{query}"
        Response Type: {response_type}
        Raw Response: "{response_text}"

        Please optimize this response and return a JSON object with:
        {{
            "processed_response": "optimized response text",
            "response_structure": {{
                "has_multiple_parts": true/false,
                "main_answer": "primary answer",
                "sub_answers": [
                    {{
                        "title": "sub-answer title",
                        "content": "sub-answer content",
                        "type": "factual|analytical|procedural|comparative"
                    }}
                ],
                "summary": "brief summary",
                "sources": ["list of sources"],
                "confidence": 0.0-1.0
            }},
            "ui_optimization": {{
                "suggested_format": "single|split|structured|conversational",
                "key_points": ["list of key points"],
                "action_items": ["list of suggested actions"],
                "follow_up_questions": ["suggested follow-up questions"]
            }},
            "metadata": {{
                "response_length": "short|medium|long",
                "complexity": "simple|moderate|complex",
                "requires_formatting": true/false,
                "has_tables": true/false,
                "has_lists": true/false
            }}
        }}

        Guidelines:
        - Make the response clear and easy to read
        - Structure complex answers logically
        - Highlight key information
        - Suggest relevant follow-up actions
        - Optimize for mobile and desktop viewing
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": processing_prompt}],
            max_tokens=1500,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error processing final response: {e}")
        return json.dumps({"error": str(e)})

@function_tool
def split_response_tool(response_text: str, max_length: int = 500) -> str:
    """Split long responses into manageable chunks for UI display"""
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        splitting_prompt = f"""
        Split the following response into logical, manageable chunks for UI display:

        Response: "{response_text}"
        Max Length per Chunk: {max_length} characters

        Return a JSON object with:
        {{
            "total_chunks": number,
            "chunks": [
                {{
                    "chunk_id": 1,
                    "title": "chunk title",
                    "content": "chunk content",
                    "length": character_count,
                    "type": "introduction|main_content|summary|action_items",
                    "order": 1
                }}
            ],
            "navigation": {{
                "has_previous": true/false,
                "has_next": true/false,
                "chunk_titles": ["list of all chunk titles"]
            }},
            "ui_hints": {{
                "show_progress": true/false,
                "allow_navigation": true/false,
                "suggested_layout": "single|split|accordion|tabs"
            }}
        }}

        Guidelines:
        - Split at logical boundaries (paragraphs, sections)
        - Keep related information together
        - Ensure each chunk is self-contained
        - Maintain flow and context
        - Prioritize readability over exact length limits
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": splitting_prompt}],
            max_tokens=2000,
            temperature=0.2
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error splitting response: {e}")
        return json.dumps({"error": str(e)})

@function_tool
def format_for_ui_tool(response_data: str, ui_type: str = "web") -> str:
    """Format response data for specific UI types (web, mobile, chat)"""
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        formatting_prompt = f"""
        Format the following response data for optimal display on {ui_type} UI:

        Response Data: {response_data}
        UI Type: {ui_type}

        Return a JSON object with:
        {{
            "formatted_response": {{
                "html": "HTML formatted response",
                "markdown": "Markdown formatted response",
                "plain_text": "Plain text response",
                "structured_data": {{
                    "sections": [
                        {{
                            "title": "section title",
                            "content": "section content",
                            "type": "text|list|table|code",
                            "styling": "normal|highlighted|warning|info"
                        }}
                    ]
                }}
            }},
            "ui_components": {{
                "buttons": [
                    {{
                        "text": "button text",
                        "action": "button action",
                        "type": "primary|secondary|link"
                    }}
                ],
                "cards": [
                    {{
                        "title": "card title",
                        "content": "card content",
                        "type": "info|warning|success|error"
                    }}
                ],
                "tables": [
                    {{
                        "headers": ["header1", "header2"],
                        "rows": [["row1col1", "row1col2"]],
                        "caption": "table caption"
                    }}
                ]
            }},
            "interactions": {{
                "expandable_sections": ["list of expandable content"],
                "collapsible_lists": ["list of collapsible items"],
                "hover_tooltips": ["list of tooltip content"],
                "click_actions": ["list of clickable actions"]
            }},
            "responsive_design": {{
                "mobile_optimized": true/false,
                "tablet_optimized": true/false,
                "desktop_optimized": true/false,
                "accessibility_features": ["list of accessibility features"]
            }}
        }}

        Guidelines for {ui_type}:
        - Use appropriate formatting for the UI type
        - Ensure mobile responsiveness
        - Include interactive elements where helpful
        - Maintain accessibility standards
        - Optimize for the specific UI context
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": formatting_prompt}],
            max_tokens=2000,
            temperature=0.2
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error formatting for UI: {e}")
        return json.dumps({"error": str(e)})

@function_tool
def generate_ui_metadata_tool(response_text: str, query: str) -> str:
    """Generate UI metadata for enhanced user experience"""
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        metadata_prompt = f"""
        Generate comprehensive UI metadata for the following response:

        Query: "{query}"
        Response: "{response_text}"

        Return a JSON object with:
        {{
            "user_experience": {{
                "estimated_read_time": "X minutes",
                "complexity_level": "beginner|intermediate|advanced",
                "requires_scrolling": true/false,
                "has_interactive_elements": true/false,
                "suggested_actions": ["action1", "action2"]
            }},
            "content_analysis": {{
                "has_tables": true/false,
                "has_lists": true/false,
                "has_code": true/false,
                "has_images": true/false,
                "has_links": true/false,
                "content_types": ["text", "data", "instructions"]
            }},
            "navigation": {{
                "has_sections": true/false,
                "section_count": number,
                "suggested_bookmarks": ["bookmark1", "bookmark2"],
                "table_of_contents": ["item1", "item2"]
            }},
            "engagement": {{
                "suggested_questions": ["question1", "question2"],
                "related_topics": ["topic1", "topic2"],
                "follow_up_suggestions": ["suggestion1", "suggestion2"],
                "sharing_options": ["email", "social", "export"]
            }},
            "accessibility": {{
                "screen_reader_friendly": true/false,
                "keyboard_navigable": true/false,
                "high_contrast_support": true/false,
                "text_size_options": ["small", "medium", "large"]
            }},
            "performance": {{
                "load_priority": "high|medium|low",
                "caching_recommended": true/false,
                "preload_suggestions": ["resource1", "resource2"]
            }}
        }}
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": metadata_prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating UI metadata: {e}")
        return json.dumps({"error": str(e)})

# ============================================================================
# QUERY ANALYSIS TOOLS
# ============================================================================

@function_tool
def analyze_query_complexity_tool(user_query: str) -> str:
    """Analyze query complexity and determine processing strategy"""
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        analysis_prompt = f"""
        Analyze the following user query and determine its complexity and processing requirements:

        User Query: "{user_query}"

        Please analyze and return a JSON object with:
        {{
            "complexity": "simple|moderate|complex|multi-part",
            "query_type": "question|command|request|conversation",
            "intent": "search|upload|process|analyze|compare|summarize|other",
            "requires_document_processing": true/false,
            "requires_vector_search": true/false,
            "requires_graph_search": true/false,
            "requires_ocr": true/false,
            "requires_table_extraction": true/false,
            "sub_queries": ["list of sub-questions if multi-part"],
            "processing_strategy": "single-step|multi-step|parallel|sequential",
            "estimated_tools_needed": ["list of tools that might be needed"],
            "confidence": 0.0-1.0
        }}

        Be thorough in your analysis and consider all possible interpretations.
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return json.dumps({"error": str(e)})

@function_tool
def decompose_complex_query_tool(user_query: str) -> str:
    """Decompose complex queries into individual sub-questions"""
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        decomposition_prompt = f"""
        Decompose the following complex query into individual, actionable sub-questions:

        User Query: "{user_query}"

        Return a JSON object with:
        {{
            "is_multi_part": true/false,
            "sub_queries": [
                {{
                    "question": "specific question text",
                    "question_type": "factual|analytical|comparative|procedural|creative",
                    "priority": 1-5,
                    "context": "brief context for this question",
                    "dependencies": ["list of other sub-queries this depends on"],
                    "tools_needed": ["list of tools needed for this sub-query"]
                }}
            ],
            "execution_order": ["ordered list of sub-query IDs"],
            "original_query": "original user query",
            "decomposition_notes": "any notes about the decomposition"
        }}

        If the query is already simple, return it as a single sub-query.
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": decomposition_prompt}],
            max_tokens=800,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error decomposing query: {e}")
        return json.dumps({"error": str(e)})

# ============================================================================
# INTELLIGENT AGENT
# ============================================================================

intelligent_agent = Agent(
    name="KnowledgeBot Intelligent Agent",
    instructions="""
You are the KnowledgeBot Intelligent Agent - the central orchestrator for all knowledge management operations.

## 🎯 CORE MISSION
You are the single point of intelligence that handles ALL user requests, makes ALL decisions, and coordinates ALL microservices. You understand, analyze, decompose, and execute complex requests with perfect precision.

## 🧠 INTELLIGENCE CAPABILITIES
- **Query Understanding**: Analyze any request, no matter how complex
- **Multi-Part Processing**: Handle multiple questions in a single request
- **Tool Orchestration**: Coordinate all microservices intelligently
- **Decision Making**: Choose the right tools and strategies
- **Response Synthesis**: Combine results into coherent answers

## 📋 AVAILABLE MICROSERVICES & TOOLS

### Document Management:
- **get_presigned_url_tool**: Get S3 upload URLs for file uploads
- **read_s3_document_tool**: Read documents from S3 storage
- **chunk_text_tool**: Split text into processable chunks

### AI & ML Processing:
- **generate_embeddings_tool**: Create vector embeddings for text
- **rag_search_tool**: Comprehensive search across all databases
- **process_pdf_tool**: Advanced PDF processing and extraction
- **process_ocr_tool**: OCR processing for images/scanned docs
- **detect_tables_tool**: Table detection and extraction
- **process_docling_core_tool**: Core document processing with Docling
- **process_docling_ocr_tool**: Advanced OCR with Docling

### Database Operations:
- **search_pinecone_tool**: Vector similarity search
- **upsert_pinecone_tool**: Store vectors in Pinecone
- **search_neo4j_tool**: Graph database search
- **write_neo4j_tool**: Write to graph database
- **read_dynamodb_tool**: Read from DynamoDB
- **write_dynamodb_tool**: Write to DynamoDB

### Query Analysis:
- **analyze_query_complexity_tool**: Analyze request complexity
- **decompose_complex_query_tool**: Break down complex queries

### Response Processing:
- **process_final_response_tool**: Optimize responses for UI display
- **split_response_tool**: Split long responses into manageable chunks
- **format_for_ui_tool**: Format responses for specific UI types
- **generate_ui_metadata_tool**: Generate UI metadata for enhanced UX

## 🔄 PROCESSING WORKFLOW

### 1. REQUEST ANALYSIS
**ALWAYS START HERE** - Use `analyze_query_complexity_tool` to understand:
- Query complexity and type
- Required processing steps
- Tools needed
- Processing strategy

### 2. QUERY DECOMPOSITION (if complex)
For multi-part queries, use `decompose_complex_query_tool` to:
- Break into individual sub-questions
- Determine execution order
- Identify dependencies
- Plan tool usage

### 3. EXECUTION STRATEGY
Based on analysis, choose execution approach:
- **Single-step**: Simple queries requiring one tool
- **Sequential**: Multi-step queries with dependencies
- **Parallel**: Independent operations that can run simultaneously
- **Hybrid**: Combination of sequential and parallel steps

### 4. TOOL COORDINATION
Execute tools in optimal order:
- **Document Upload**: presigned_url → s3_reader → processing
- **Document Processing**: Choose appropriate processor (PDF, OCR, Docling)
- **Text Processing**: chunk_text → generate_embeddings → store_vectors
- **Search Operations**: rag_search → database_operations → synthesis
- **Multi-Database**: Coordinate Pinecone, Neo4j, DynamoDB operations

### 5. RESPONSE SYNTHESIS
Combine all results into coherent responses:
- **Single Query**: Direct, comprehensive answer
- **Multi-Part**: Structured response addressing each sub-question
- **Complex Analysis**: Detailed breakdown with sources and reasoning

### 6. RESPONSE PROCESSING & UI OPTIMIZATION
**ALWAYS END HERE** - Process the final response for optimal UI display:
- **process_final_response_tool**: Optimize response structure and content
- **split_response_tool**: Split long responses if needed (>500 chars)
- **format_for_ui_tool**: Format for specific UI type (web/mobile/chat)
- **generate_ui_metadata_tool**: Generate UI metadata for enhanced UX

## 📝 RESPONSE STRUCTURES

### Single Question Response:
```
**Answer**: [Comprehensive answer with full context]

**Sources**: [List of sources and references used]

**Processing Details**: [Brief explanation of tools used]
```

### Multi-Part Query Response:
```
**Query Analysis**: [Brief analysis of the complex query]

**Answer 1: [First Sub-Question]**
[Detailed answer with sources]

**Answer 2: [Second Sub-Question]**
[Detailed answer with sources]

**Answer 3: [Third Sub-Question]**
[Detailed answer with sources]

**Summary**: [Overall synthesis connecting all answers]

**Processing Summary**: [Tools used and execution strategy]
```

### Document Processing Response:
```
**Processing Status**: [Success/Failure with details]

**Document Analysis**: [What was extracted and processed]

**Content Summary**: [Key information found]

**Stored Information**: [What was saved to databases]

**Next Steps**: [What can be done with this document]
```

## 🎯 DECISION MAKING GUIDELINES

### Document Type Detection:
- **PDF**: Use `process_pdf_tool` or `process_docling_core_tool`
- **Scanned PDF**: Use `process_ocr_tool` or `process_docling_ocr_tool`
- **Images**: Use `process_ocr_tool`
- **Tables**: Use `detect_tables_tool`
- **Complex Documents**: Use `process_docling_ocr_tool`

### Search Strategy Selection:
- **Simple Search**: Use `rag_search_tool`
- **Vector Search**: Use `search_pinecone_tool`
- **Graph Search**: Use `search_neo4j_tool`
- **Metadata Search**: Use `read_dynamodb_tool`

### Processing Pipeline:
- **New Document**: Upload → Process → Chunk → Embed → Store
- **Search Query**: Analyze → Search → Synthesize → Respond
- **Complex Analysis**: Decompose → Process Each Part → Synthesize

## 🚨 ERROR HANDLING
- **Tool Failures**: Try alternative approaches, explain limitations
- **Partial Results**: Acknowledge what worked and what didn't
- **Timeout Issues**: Break down into smaller operations
- **Data Issues**: Suggest corrections or alternative approaches

## 💡 INTELLIGENCE PRINCIPLES
1. **Always Analyze First**: Understand before acting
2. **Decompose Complex Queries**: Break down multi-part requests
3. **Choose Optimal Tools**: Select best microservice for each task
4. **Coordinate Efficiently**: Minimize redundant operations
5. **Synthesize Comprehensively**: Combine all results meaningfully
6. **Handle Errors Gracefully**: Provide helpful error messages
7. **Be Transparent**: Explain your reasoning and process

## 🎪 EXAMPLE SCENARIOS

### Scenario 1: Document Upload & Processing
```
User: "Upload this PDF and tell me what's in it"
1. analyze_query_complexity_tool → "upload + analysis request"
2. get_presigned_url_tool → Get upload URL
3. read_s3_document_tool → Read uploaded document
4. process_docling_core_tool → Extract content
5. chunk_text_tool → Create chunks
6. generate_embeddings_tool → Create vectors
7. upsert_pinecone_tool → Store vectors
8. write_dynamodb_tool → Store metadata
9. Synthesize → Comprehensive document summary
```

### Scenario 2: Complex Multi-Part Query
```
User: "What are the main topics in my documents, which ones discuss AI, and how do they relate to each other?"
1. analyze_query_complexity_tool → "complex multi-part analysis"
2. decompose_complex_query_tool → Break into sub-questions
3. rag_search_tool → Find relevant documents
4. search_neo4j_tool → Find relationships
5. Process each sub-question → Individual answers
6. Synthesize → Comprehensive analysis with relationships
```

### Scenario 3: Search & Analysis
```
User: "Find all documents about machine learning and compare their approaches"
1. analyze_query_complexity_tool → "search + comparison"
2. rag_search_tool → Find ML documents
3. read_dynamodb_tool → Get document details
4. search_neo4j_tool → Find relationships
5. Synthesize → Comparative analysis
```

## 🔥 CRITICAL SUCCESS FACTORS
- **Always start with analysis** - understand the request fully
- **Decompose complex queries** - break down multi-part requests
- **Choose the right tools** - match tools to requirements
- **Coordinate efficiently** - minimize redundant operations
- **Synthesize comprehensively** - combine all results meaningfully
- **Handle errors gracefully** - provide helpful error messages
- **Be transparent** - explain your reasoning and process

Remember: You are the INTELLIGENCE. You make ALL decisions. You coordinate ALL tools. You provide ALL answers. Be thorough, be intelligent, be helpful.
""",
    model="gpt-4o-mini",
    tools=[
        # Query Analysis Tools
        analyze_query_complexity_tool,
        decompose_complex_query_tool,
        
        # Document Management Tools
        get_presigned_url_tool,
        read_s3_document_tool,
        chunk_text_tool,
        
        # AI & ML Processing Tools
        generate_embeddings_tool,
        rag_search_tool,
        process_pdf_tool,
        process_ocr_tool,
        detect_tables_tool,
        process_docling_core_tool,
        process_docling_ocr_tool,
        
        # Database Operations Tools
        search_pinecone_tool,
        upsert_pinecone_tool,
        search_neo4j_tool,
        write_neo4j_tool,
        read_dynamodb_tool,
        write_dynamodb_tool,
        
        # Response Processing Tools
        process_final_response_tool,
        split_response_tool,
        format_for_ui_tool,
        generate_ui_metadata_tool,
    ]
)

logger.info("✅ Intelligent Agent created with comprehensive tools and instructions")

# ============================================================================
# LAMBDA HANDLER
# ============================================================================

async def intelligent_agent_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main intelligent agent handler"""
    try:
        logger.info("🤖 Intelligent Agent processing request")
        
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        user_query = body.get('query') or body.get('message') or body.get('text', '')
        conversation_history = body.get('conversation_history', [])
        user_preferences = body.get('user_preferences', {})
        
        if not user_query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Query is required"})
            }
        
        logger.info(f"📝 Processing query: {user_query[:100]}...")
        
        # Run the intelligent agent
        result = await Runner.run(
            intelligent_agent,
            input=user_query
        )
        
        # Extract response
        try:
            response_text = result.final_output
        except Exception as e:
            response_text = f"Error generating response: {str(e)}"
        
        # Process response for UI optimization
        try:
            logger.info("🎨 Processing response for UI optimization")
            
            # Process final response
            processed_response = await Runner.run(
                intelligent_agent,
                input=f"Process this response for UI display: {response_text}"
            )
            
            # Extract processed response
            try:
                ui_optimized_response = processed_response.final_output
            except Exception as e:
                ui_optimized_response = response_text
            
            logger.info("✅ Response processing completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Response processing failed, using original: {e}")
            ui_optimized_response = response_text
        
        logger.info("✅ Intelligent Agent completed successfully")
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "response": ui_optimized_response,
                "original_response": response_text,
                "query": user_query,
                "timestamp": datetime.now().isoformat(),
                "agent": "intelligent-agent",
                "ui_optimized": True
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Intelligent Agent error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler entry point"""
    return asyncio.run(intelligent_agent_handler_async(event, context))
