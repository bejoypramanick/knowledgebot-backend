#!/usr/bin/env python3
"""
Simple test handler to isolate the entrypoint issue
"""

import json
import sys
import os

def lambda_handler(event, context):
    """Simple test handler with detailed logging"""
    print("=== LAMBDA HANDLER STARTED ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Environment variables: {dict(os.environ)}")
    print(f"Event received: {json.dumps(event, indent=2)}")
    print(f"Context: {context}")
    
    try:
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Hello from test handler!',
                'event': event,
                'python_version': sys.version,
                'working_directory': os.getcwd()
            })
        }
        print(f"Returning result: {json.dumps(result, indent=2)}")
        print("=== LAMBDA HANDLER COMPLETED SUCCESSFULLY ===")
        return result
    except Exception as e:
        print(f"ERROR in lambda_handler: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': str(type(e))
            })
        }
