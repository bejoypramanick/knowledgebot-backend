#!/usr/bin/env python3
"""
CORS Helper Functions
Comprehensive CORS handling for all Lambda functions
"""

def get_cors_headers(origin: str = "*") -> dict:
    """Get standard CORS headers"""
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400"
    }

def handle_cors_preflight(event: dict) -> dict:
    """Handle CORS preflight OPTIONS request"""
    return {
        "statusCode": 200,
        "headers": get_cors_headers(),
        "body": ""
    }

def create_cors_response(status_code: int, body: dict, origin: str = "*") -> dict:
    """Create response with CORS headers"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            **get_cors_headers(origin)
        },
        "body": json.dumps(body) if isinstance(body, dict) else body
    }

def create_error_response(error_message: str, status_code: int = 500, origin: str = "*") -> dict:
    """Create error response with CORS headers"""
    return create_cors_response(status_code, {
        "error": error_message,
        "success": False
    }, origin)
