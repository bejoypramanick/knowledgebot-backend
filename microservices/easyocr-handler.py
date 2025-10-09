#!/usr/bin/env python3
"""
EasyOCR Processor - Single Purpose Lambda
Performs OCR on images and scanned documents
"""

import json
import os
from typing import Dict, Any, List
import logging
import base64
import io

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize OCR libraries
try:
    import easyocr
    import cv2
    import numpy as np
    from PIL import Image
    import pytesseract
    logger.info("OCR libraries initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OCR libraries: {e}")
    easyocr = None
    cv2 = None
    np = None
    Image = None
    pytesseract = None

def perform_ocr(image_bytes: bytes, languages: List[str] = ['en']) -> Dict[str, Any]:
    """Perform OCR on image using multiple methods"""
    results = {
        "easyocr": None,
        "tesseract": None,
        "combined_text": "",
        "detected_text": []
    }
    
    try:
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Method 1: EasyOCR
        if easyocr:
            reader = easyocr.Reader(languages)
            easyocr_results = reader.readtext(image_array)
            
            easyocr_text = ""
            for (bbox, text, confidence) in easyocr_results:
                easyocr_text += text + " "
                results["detected_text"].append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": bbox,
                    "method": "easyocr"
                })
            
            results["easyocr"] = easyocr_text.strip()
        
        # Method 2: Tesseract
        if pytesseract:
            tesseract_text = pytesseract.image_to_string(image)
            results["tesseract"] = tesseract_text.strip()
            
            # Get detailed data
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    results["detected_text"].append({
                        "text": data['text'][i],
                        "confidence": int(data['conf'][i]) / 100.0,
                        "bbox": [data['left'][i], data['top'][i], 
                                data['width'][i], data['height'][i]],
                        "method": "tesseract"
                    })
        
        # Combine all text
        all_texts = [results["easyocr"], results["tesseract"]]
        combined_text = " ".join([text for text in all_texts if text])
        results["combined_text"] = combined_text
        
        return {
            "success": True,
            "results": results,
            "total_text_length": len(combined_text),
            "total_detections": len(results["detected_text"])
        }
        
    except Exception as e:
        logger.error(f"Error performing OCR: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Perform OCR on image"""
    logger.info("=== EASYOCR PROCESSOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        image_bytes_b64 = body.get('image_bytes', '')
        languages = body.get('languages', ['en'])
        
        if not image_bytes_b64:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Image bytes are required"})
            }
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_bytes_b64)
        
        # Perform OCR
        result = perform_ocr(image_bytes, languages)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in EasyOCR processor: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
