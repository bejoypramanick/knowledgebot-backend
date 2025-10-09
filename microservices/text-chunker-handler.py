#!/usr/bin/env python3
"""
Text Chunker - Single Purpose Lambda
Chunks text into smaller pieces for processing
"""

import json
import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """Chunk text into smaller pieces"""
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + chunk_size // 2:
                end = sentence_end + 1
            else:
                # Look for word boundary
                word_end = text.rfind(' ', start, end)
                if word_end > start + chunk_size // 2:
                    end = word_end
        
        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append({
                "text": chunk_text_content,
                "start_pos": start,
                "end_pos": end,
                "chunk_size": len(chunk_text_content),
                "chunk_index": len(chunks)
            })
        
        # Move start position with overlap
        start = end - chunk_overlap
        if start >= len(text):
            break
    
    return chunks

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Chunk text into smaller pieces"""
    logger.info("=== TEXT CHUNKER STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        text = body.get('text', '')
        chunk_size = body.get('chunk_size', 1000)
        chunk_overlap = body.get('chunk_overlap', 200)
        
        if not text:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Text is required"})
            }
        
        # Chunk the text
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "original_length": len(text),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            })
        }
        
    except Exception as e:
        logger.error(f"Error chunking text: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
