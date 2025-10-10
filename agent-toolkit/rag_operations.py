"""
Production RAG Operations
Complete RAG pipeline for document ingestion and retrieval with Docling integration

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from crud_operations import (
    generate_embedding_crud,
    search_pinecone_crud,
    upsert_pinecone_crud,
    search_neo4j_crud,
    execute_neo4j_write_crud,
    read_dynamodb_crud,
    write_dynamodb_crud,
    NEO4J_AVAILABLE
)
from docling_processor import get_docling_processor, DocumentProcessingResult

logger = logging.getLogger(__name__)

def rag_search_crud(query: str, limit: int = 5, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Complete RAG search pipeline
    
    Args:
        query: User query text
        limit: Maximum number of results
        filter_dict: Pinecone metadata filter
        namespace: Pinecone namespace
        
    Returns:
        RAG search results with context
    """
    try:
        # Step 1: Generate embedding
        embedding_result = generate_embedding_crud(query)
        if not embedding_result['success']:
            return embedding_result
        
        # Step 2: Search Pinecone
        search_result = search_pinecone_crud(
            query_vector=embedding_result['embedding'],
            limit=limit,
            filter_dict=filter_dict,
            namespace=namespace
        )
        
        if not search_result['success']:
            return search_result
        
        # Step 3: Get additional context from Neo4j
        neo4j_context = []
        if search_result['matches']:
            # Extract document IDs from Pinecone results
            doc_ids = [match['document_id'] for match in search_result['matches'] if match.get('document_id')]
            
            if doc_ids:
                # Query Neo4j for relationships
                cypher_query = """
                MATCH (d:Document)-[r]-(related)
                WHERE d.id IN $doc_ids
                RETURN d.id as document_id, 
                       type(r) as relationship_type, 
                       related.id as related_id,
                       related.title as related_title,
                       related.type as related_type
                LIMIT 20
                """
                
                neo4j_result = search_neo4j_crud(cypher_query, {'doc_ids': doc_ids})
                if neo4j_result['success']:
                    neo4j_context = neo4j_result['data']
        
        # Step 4: Get detailed metadata from DynamoDB
        dynamodb_context = []
        if search_result['matches']:
            # Get document metadata for each match
            for match in search_result['matches']:
                if match.get('document_id'):
                    doc_result = read_dynamodb_crud(
                        table_name=os.environ.get('DYNAMODB_TABLE', 'chatbot-knowledge-base-metadata'),
                        key={'document_id': match['document_id']}
                    )
                    if doc_result['success']:
                        dynamodb_context.append(doc_result['data'])
        
        return {
            'success': True,
            'query': query,
            'matches': search_result['matches'],
            'neo4j_context': neo4j_context,
            'dynamodb_context': dynamodb_context,
            'total_matches': search_result['total_matches'],
            'namespace': search_result['namespace']
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query': query
        }

def rag_upsert_document_crud(document_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any], namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Complete RAG document ingestion pipeline
    
    Args:
        document_id: Unique document identifier
        chunks: List of text chunks with metadata
        metadata: Document metadata
        namespace: Pinecone namespace
        
    Returns:
        Upsert result
    """
    try:
        results = {
            'success': True,
            'document_id': document_id,
            'chunks_processed': 0,
            'pinecone_upserted': 0,
            'dynamodb_stored': 0,
            'neo4j_created': 0,
            'errors': []
        }
        
        # Step 1: Process each chunk
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding_result = generate_embedding_crud(chunk['text'])
                if not embedding_result['success']:
                    results['errors'].append(f"Chunk {i}: {embedding_result['error']}")
                    continue
                
                # Prepare vector for Pinecone
                chunk_id = f"{document_id}_chunk_{i}"
                vector_data = {
                    'id': chunk_id,
                    'values': embedding_result['embedding'],
                    'metadata': {
                        'text': chunk['text'],
                        'document_id': document_id,
                        'chunk_id': chunk_id,
                        'chunk_index': i,
                        'source': metadata.get('source', ''),
                        'title': metadata.get('title', ''),
                        'author': metadata.get('author', ''),
                        'created_at': datetime.now().isoformat(),
                        **chunk.get('metadata', {})
                    }
                }
                vectors_to_upsert.append(vector_data)
                results['chunks_processed'] += 1
                
            except Exception as e:
                results['errors'].append(f"Chunk {i}: {str(e)}")
        
        # Step 2: Upsert to Pinecone
        if vectors_to_upsert:
            pinecone_result = upsert_pinecone_crud(vectors_to_upsert, namespace)
            if pinecone_result['success']:
                results['pinecone_upserted'] = len(vectors_to_upsert)
            else:
                results['errors'].append(f"Pinecone upsert: {pinecone_result['error']}")
        
        # Step 3: Store metadata in DynamoDB
        dynamodb_item = {
            'document_id': document_id,
            'title': metadata.get('title', ''),
            'source': metadata.get('source', ''),
            'author': metadata.get('author', ''),
            'content_type': metadata.get('content_type', ''),
            'chunk_count': len(chunks),
            'created_at': datetime.now().isoformat(),
            'status': 'processed',
            'metadata': metadata
        }
        
        dynamodb_result = write_dynamodb_crud(
            table_name=os.environ.get('DYNAMODB_TABLE', 'chatbot-knowledge-base-metadata'),
            item=dynamodb_item
        )
        if dynamodb_result['success']:
            results['dynamodb_stored'] = 1
        else:
            results['errors'].append(f"DynamoDB write: {dynamodb_result['error']}")
        
        # Step 4: Create Neo4j relationships
        if vectors_to_upsert:
            try:
                # Create document node
                create_doc_query = """
                MERGE (d:Document {id: $document_id})
                SET d.title = $title,
                    d.source = $source,
                    d.author = $author,
                    d.created_at = $created_at
                """
                
                neo4j_result = execute_neo4j_write_crud(create_doc_query, {
                    'document_id': document_id,
                    'title': metadata.get('title', ''),
                    'source': metadata.get('source', ''),
                    'author': metadata.get('author', ''),
                    'created_at': datetime.now().isoformat()
                })
                
                if neo4j_result['success']:
                    results['neo4j_created'] += 1
                else:
                    results['errors'].append(f"Neo4j document: {neo4j_result['error']}")
                
                # Create chunk nodes and relationships
                for chunk in vectors_to_upsert:
                    chunk_query = """
                    MATCH (d:Document {id: $document_id})
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.text = $text,
                        c.chunk_index = $chunk_index,
                        c.created_at = $created_at
                    MERGE (d)-[:CONTAINS]->(c)
                    """
                    
                    execute_neo4j_write_crud(chunk_query, {
                        'document_id': document_id,
                        'chunk_id': chunk['id'],
                        'text': chunk['metadata']['text'],
                        'chunk_index': chunk['metadata']['chunk_index'],
                        'created_at': chunk['metadata']['created_at']
                    })
                
            except Exception as e:
                results['errors'].append(f"Neo4j relationships: {str(e)}")
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }

def rag_chunk_document_crud(document_text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    CRUD: Chunk document text for RAG processing
    
    Args:
        document_text: Full document text
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    try:
        chunks = []
        start = 0
        
        while start < len(document_text):
            end = start + chunk_size
            chunk_text = document_text[start:end]
            
            # Try to break at sentence boundary
            if end < len(document_text):
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:  # Don't make chunks too small
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append({
                'text': chunk_text.strip(),
                'start_pos': start,
                'end_pos': end,
                'chunk_size': len(chunk_text)
            })
            
            start = end - chunk_overlap
            if start >= len(document_text):
                break
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error chunking document: {e}")
        return [{'text': document_text, 'start_pos': 0, 'end_pos': len(document_text), 'chunk_size': len(document_text)}]

def rag_process_document_with_docling_crud(document_path: str, document_id: str = None, namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Process document with intelligent Docling routing
    
    Args:
        document_path: Path to document (S3 URI or local path)
        document_id: Optional document ID
        namespace: Pinecone namespace
        
    Returns:
        Processing result with hierarchical chunks
    """
    try:
        # Read document bytes
        if document_path.startswith('s3://'):
            # Read from S3
            import boto3
            s3 = boto3.client('s3')
            bucket, key = document_path[5:].split('/', 1)
            response = s3.get_object(Bucket=bucket, Key=key)
            document_bytes = response['Body'].read()
            filename = key.split('/')[-1]
        else:
            # Read from local path
            with open(document_path, 'rb') as f:
                document_bytes = f.read()
            filename = Path(document_path).name
        
        # Use intelligent document orchestrator
        orchestrator_result = call_document_orchestrator(document_bytes, filename, document_id)
        
        if not orchestrator_result.get('success'):
            return {
                'success': False,
                'error': f"Document processing failed: {orchestrator_result.get('error', 'Unknown error')}",
                'document_id': document_id,
                'docling_fallback_used': False
            }
        
        # Convert result to RAG format
        rag_chunks = []
        
        # Handle different result formats
        if 'hierarchical_chunks' in orchestrator_result:
            # Docling full result
            for chunk in orchestrator_result['hierarchical_chunks']:
                rag_chunk = {
                    'text': chunk.get('content', ''),
                    'metadata': {
                        'chunk_id': chunk.get('chunk_id', f"{document_id}_chunk_{len(rag_chunks)}"),
                        'chunk_type': chunk.get('element_type', 'text'),
                        'hierarchy_level': chunk.get('hierarchy_level', 0),
                        'section_path': chunk.get('section_path', ''),
                        'word_count': len(chunk.get('content', '').split()),
                        'char_count': len(chunk.get('content', '')),
                        'page_number': chunk.get('page_number'),
                        'confidence_score': chunk.get('confidence', 1.0),
                        'chunk_index': len(rag_chunks)
                    }
                }
                rag_chunks.append(rag_chunk)
        
        elif 'pages' in orchestrator_result:
            # PDF with pages
            for page in orchestrator_result['pages']:
                rag_chunk = {
                    'text': page.get('text', ''),
                    'metadata': {
                        'chunk_id': f"{document_id}_page_{page.get('page_number', len(rag_chunks))}",
                        'chunk_type': 'page',
                        'hierarchy_level': 0,
                        'section_path': f"Page {page.get('page_number', len(rag_chunks))}",
                        'word_count': len(page.get('text', '').split()),
                        'char_count': len(page.get('text', '')),
                        'page_number': page.get('page_number'),
                        'confidence_score': page.get('ocr_confidence', 1.0),
                        'chunk_index': len(rag_chunks)
                    }
                }
                rag_chunks.append(rag_chunk)
        
        else:
            # Simple text result
            text = orchestrator_result.get('text', '')
            if text:
                rag_chunk = {
                    'text': text,
                    'metadata': {
                        'chunk_id': f"{document_id}_chunk_0",
                        'chunk_type': 'text',
                        'hierarchy_level': 0,
                        'section_path': 'Document',
                        'word_count': len(text.split()),
                        'char_count': len(text),
                        'page_number': 1,
                        'confidence_score': 1.0,
                        'chunk_index': 0
                    }
                }
                rag_chunks.append(rag_chunk)
        
        # Store in RAG system
        if rag_chunks:
            upsert_result = rag_upsert_document_crud(
                document_id=document_id or orchestrator_result.get('document_id'),
                chunks=rag_chunks,
                metadata=orchestrator_result.get('metadata', {}),
                namespace=namespace
            )
            
            return {
                'success': True,
                'document_id': document_id or orchestrator_result.get('document_id'),
                'document_type': orchestrator_result.get('file_extension', 'unknown'),
                'total_chunks': len(rag_chunks),
                'hierarchical_chunks': rag_chunks,
                'processing_time': orchestrator_result.get('processing_time', 0),
                'upsert_result': upsert_result,
                'metadata': orchestrator_result.get('metadata', {}),
                'processing_strategy': orchestrator_result.get('processing_strategy', 'unknown'),
                'analysis': orchestrator_result.get('analysis', {})
            }
        else:
            return {
                'success': False,
                'error': 'No chunks generated from document',
                'document_id': document_id
            }
            
    except Exception as e:
        logger.error(f"Error processing document with intelligent Docling: {e}")
        return {
            'success': False,
            'error': f"Document processing failed: {str(e)}",
            'document_id': document_id,
            'docling_fallback_used': False
        }

def call_document_orchestrator(document_bytes: bytes, filename: str, document_id: str = None) -> Dict[str, Any]:
    """
    Call the document orchestrator service
    """
    try:
        import aiohttp
        import asyncio
        import base64
        
        async def _call_orchestrator():
            orchestrator_url = os.environ.get('DOCUMENT_ORCHESTRATOR_URL', 'http://localhost:8080')
            
            payload = {
                'document_bytes': base64.b64encode(document_bytes).decode(),
                'filename': filename,
                'document_id': document_id
            }
            
            async with aiohttp.ClientSession() as client:
                async with client.post(f"{orchestrator_url}/document-orchestrator", json=payload) as response:
                    return await response.json()
        
        # Run async call
        return asyncio.run(_call_orchestrator())
        
    except Exception as e:
        logger.error(f"Failed to call document orchestrator: {e}")
        return {
            'success': False,
            'error': f"Orchestrator call failed: {str(e)}"
        }

def rag_process_document_from_bytes_crud(document_bytes: bytes, filename: str, document_id: str = None, namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Process document from bytes using Docling (useful for S3 documents)
    
    Args:
        document_bytes: Document content as bytes
        filename: Original filename
        document_id: Optional document ID
        namespace: Pinecone namespace
        
    Returns:
        Processing result with hierarchical chunks
    """
    try:
        # Get Docling processor
        processor = get_docling_processor()
        
        # Process document from bytes
        result = processor.process_document_from_bytes(document_bytes, filename, document_id)
        
        if not result.success:
            return {
                'success': False,
                'error': f"Docling processing failed: {result.error_message}",
                'document_id': result.document_id,
                'docling_fallback_used': False
            }
        
        # Convert Docling chunks to RAG format
        rag_chunks = []
        for chunk in result.hierarchical_chunks:
            rag_chunk = {
                'text': chunk['content'],
                'metadata': {
                    'chunk_id': chunk['chunk_id'],
                    'chunk_type': chunk['chunk_type'],
                    'hierarchy_level': chunk['hierarchy_level'],
                    'section_path': chunk['section_path'],
                    'word_count': chunk['metadata']['word_count'],
                    'char_count': chunk['metadata']['char_count'],
                    'page_number': chunk['metadata']['page_number'],
                    'confidence_score': chunk['metadata']['confidence_score'],
                    'chunk_index': chunk['metadata']['chunk_index']
                }
            }
            rag_chunks.append(rag_chunk)
        
        # Store in RAG system
        if rag_chunks:
            upsert_result = rag_upsert_document_crud(
                document_id=result.document_id,
                chunks=rag_chunks,
                metadata=result.metadata or {},
                namespace=namespace
            )
            
            return {
                'success': True,
                'document_id': result.document_id,
                'document_type': result.document_type,
                'total_chunks': result.total_chunks,
                'hierarchical_chunks': rag_chunks,
                'processing_time': result.processing_time,
                'upsert_result': upsert_result,
                'metadata': result.metadata
            }
        else:
            return {
                'success': False,
                'error': 'No chunks generated from document',
                'document_id': result.document_id
            }
            
    except Exception as e:
        logger.error(f"Error processing document from bytes with Docling: {e}")
        return {
            'success': False,
            'error': f"Docling processing failed: {str(e)}",
            'document_id': document_id,
            'docling_fallback_used': False
        }

def rag_search_with_hierarchical_context_crud(query: str, limit: int = 5, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Enhanced RAG search with hierarchical context from Docling chunks
    
    Args:
        query: User query text
        limit: Maximum number of results
        filter_dict: Pinecone metadata filter (can include chunk_type, hierarchy_level)
        namespace: Pinecone namespace
        
    Returns:
        Enhanced RAG search results with hierarchical context
    """
    try:
        # Step 1: Generate embedding
        embedding_result = generate_embedding_crud(query)
        if not embedding_result['success']:
            return embedding_result
        
        # Step 2: Search Pinecone with enhanced filter
        enhanced_filter = filter_dict or {}
        
        search_result = search_pinecone_crud(
            query_vector=embedding_result['embedding'],
            limit=limit,
            filter_dict=enhanced_filter,
            namespace=namespace
        )
        
        if not search_result['success']:
            return search_result
        
        # Step 3: Group results by hierarchy level and document
        hierarchical_results = {}
        for match in search_result['matches']:
            doc_id = match.get('document_id', 'unknown')
            chunk_type = match.get('metadata', {}).get('chunk_type', 'default')
            hierarchy_level = match.get('metadata', {}).get('hierarchy_level', 3)
            section_path = match.get('metadata', {}).get('section_path', '')
            
            if doc_id not in hierarchical_results:
                hierarchical_results[doc_id] = {
                    'document_id': doc_id,
                    'title': match.get('metadata', {}).get('title', ''),
                    'chunks_by_type': {},
                    'chunks_by_level': {},
                    'section_structure': set()
                }
            
            # Group by chunk type
            if chunk_type not in hierarchical_results[doc_id]['chunks_by_type']:
                hierarchical_results[doc_id]['chunks_by_type'][chunk_type] = []
            hierarchical_results[doc_id]['chunks_by_type'][chunk_type].append(match)
            
            # Group by hierarchy level
            if hierarchy_level not in hierarchical_results[doc_id]['chunks_by_level']:
                hierarchical_results[doc_id]['chunks_by_level'][hierarchy_level] = []
            hierarchical_results[doc_id]['chunks_by_level'][hierarchy_level].append(match)
            
            # Track section structure
            if section_path:
                hierarchical_results[doc_id]['section_structure'].add(section_path)
        
        # Step 4: Get Neo4j context for document relationships
        neo4j_context = []
        if search_result['matches']:
            doc_ids = list(hierarchical_results.keys())
            
            if doc_ids:
                cypher_query = """
                MATCH (d:Document)-[r]-(related)
                WHERE d.id IN $doc_ids
                RETURN d.id as document_id, 
                       type(r) as relationship_type, 
                       related.id as related_id,
                       related.title as related_title,
                       related.type as related_type
                LIMIT 20
                """
                
                neo4j_result = search_neo4j_crud(cypher_query, {'doc_ids': doc_ids})
                if neo4j_result['success']:
                    neo4j_context = neo4j_result['data']
        
        # Step 5: Get detailed metadata from DynamoDB
        dynamodb_context = []
        for doc_id in hierarchical_results.keys():
            doc_result = read_dynamodb_crud(
                table_name=os.environ.get('DYNAMODB_TABLE', 'chatbot-knowledge-base-metadata'),
                key={'document_id': doc_id}
            )
            if doc_result['success']:
                dynamodb_context.append(doc_result['data'])
        
        return {
            'success': True,
            'query': query,
            'matches': search_result['matches'],
            'hierarchical_results': hierarchical_results,
            'neo4j_context': neo4j_context,
            'dynamodb_context': dynamodb_context,
            'total_matches': search_result['total_matches'],
            'namespace': search_result['namespace'],
            'search_metadata': {
                'hierarchical_chunking_enabled': True,
                'documents_found': len(hierarchical_results),
                'chunk_types_found': list(set(
                    match.get('metadata', {}).get('chunk_type', 'default') 
                    for match in search_result['matches']
                )),
                'hierarchy_levels_found': list(set(
                    match.get('metadata', {}).get('hierarchy_level', 3) 
                    for match in search_result['matches']
                ))
            }
        }
        
    except Exception as e:
        logger.error(f"Error in hierarchical RAG search: {e}")
        return {
            'success': False,
            'error': str(e),
            'query': query
        }
