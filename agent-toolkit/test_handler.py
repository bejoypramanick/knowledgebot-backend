#!/usr/bin/env python3
"""
Simple test handler to isolate the entrypoint issue
"""

import json

def lambda_handler(event, context):
    """Simple test handler"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Hello from test handler!',
            'event': event
        })
    }
