#!/usr/bin/env python3
"""
Table Detector - Single Purpose Lambda
Detects and extracts table structures from documents
"""

import json
import os
from typing import Dict, Any, List
import logging
import base64
import io

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize table detection libraries
try:
    import cv2
    import numpy as np
    from PIL import Image
    import pandas as pd
    logger.info("Table detection libraries initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize table detection libraries: {e}")
    cv2 = None
    np = None
    Image = None
    pd = None

def detect_tables(image_bytes: bytes) -> Dict[str, Any]:
    """Detect table structures in image"""
    results = {
        "tables_detected": [],
        "total_tables": 0,
        "table_data": []
    }
    
    try:
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        # Detect horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # Detect horizontal lines
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=1)
        
        # Detect vertical lines
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=1)
        
        # Combine lines
        table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
        
        # Find contours
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Process each detected table
        for i, contour in enumerate(contours):
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by size (remove very small detections)
            if w > 100 and h > 50:
                table_info = {
                    "table_id": i + 1,
                    "bbox": [x, y, w, h],
                    "area": w * h,
                    "confidence": 0.8  # Placeholder confidence
                }
                
                results["tables_detected"].append(table_info)
                
                # Extract table region
                table_region = image_array[y:y+h, x:x+w]
                
                # Convert to DataFrame (simplified)
                table_data = {
                    "table_id": i + 1,
                    "data": "Table data extraction would go here",
                    "rows": 0,
                    "columns": 0
                }
                
                results["table_data"].append(table_data)
        
        results["total_tables"] = len(results["tables_detected"])
        
        return {
            "success": True,
            "results": results,
            "image_shape": image_array.shape
        }
        
    except Exception as e:
        logger.error(f"Error detecting tables: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Detect table structures in document"""
    logger.info("=== TABLE DETECTOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        image_bytes_b64 = body.get('image_bytes', '')
        
        if not image_bytes_b64:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Image bytes are required"})
            }
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_bytes_b64)
        
        # Detect tables
        result = detect_tables(image_bytes)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in table detector: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
