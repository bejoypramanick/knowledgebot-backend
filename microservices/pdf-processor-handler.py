#!/usr/bin/env python3
"""
PDF Processor - Single Purpose Lambda
Processes PDF documents for text extraction and structure
"""

import json
import os
from typing import Dict, Any, List
import logging
import base64
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize PDF processing libraries
try:
    import pypdfium2 as pdfium
    import pdfplumber
    import fitz  # PyMuPDF
    logger.info("PDF processing libraries initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize PDF libraries: {e}")
    pdfium = None
    pdfplumber = None
    fitz = None

def extract_text_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extract text from PDF using multiple methods"""
    results = {
        "pypdfium2": None,
        "pdfplumber": None,
        "pymupdf": None,
        "combined_text": "",
        "pages": []
    }
    
    try:
        # Method 1: PyPDFium2
        if pdfium:
            pdf = pdfium.PdfDocument(pdf_bytes)
            pypdfium2_text = ""
            for i in range(len(pdf)):
                page = pdf[i]
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                pypdfium2_text += text + "\n"
                results["pages"].append({
                    "page_number": i + 1,
                    "text": text,
                    "method": "pypdfium2"
                })
            results["pypdfium2"] = pypdfium2_text
            pdf.close()
        
        # Method 2: PDFPlumber
        if pdfplumber:
            import io
            pdf_file = io.BytesIO(pdf_bytes)
            with pdfplumber.open(pdf_file) as pdf:
                pdfplumber_text = ""
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pdfplumber_text += text + "\n"
                    results["pages"].append({
                        "page_number": i + 1,
                        "text": text,
                        "method": "pdfplumber"
                    })
            results["pdfplumber"] = pdfplumber_text
        
        # Method 3: PyMuPDF
        if fitz:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pymupdf_text = ""
            for i in range(pdf_doc.page_count):
                page = pdf_doc[i]
                text = page.get_text()
                pymupdf_text += text + "\n"
                results["pages"].append({
                    "page_number": i + 1,
                    "text": text,
                    "method": "pymupdf"
                })
            pdf_doc.close()
            results["pymupdf"] = pymupdf_text
        
        # Combine all text
        all_texts = [results["pypdfium2"], results["pdfplumber"], results["pymupdf"]]
        combined_text = "\n".join([text for text in all_texts if text])
        results["combined_text"] = combined_text
        
        return {
            "success": True,
            "results": results,
            "total_pages": len(results["pages"]),
            "total_text_length": len(combined_text)
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process PDF document for text extraction"""
    logger.info("=== PDF PROCESSOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        pdf_bytes_b64 = body.get('pdf_bytes', '')
        filename = body.get('filename', 'document.pdf')
        
        if not pdf_bytes_b64:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "PDF bytes are required"})
            }
        
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(pdf_bytes_b64)
        
        # Process PDF
        result = extract_text_from_pdf(pdf_bytes)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in PDF processor: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
