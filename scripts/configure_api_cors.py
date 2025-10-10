#!/usr/bin/env python3
"""
API Gateway CORS Configuration Script
Configures CORS settings for API Gateway to fix cross-origin issues
"""

import boto3
import json
import sys
from typing import Dict, Any

def configure_api_gateway_cors(api_id: str, stage_name: str = 'prod', region: str = 'ap-south-1') -> bool:
    """Configure CORS for API Gateway"""
    try:
        # Initialize API Gateway client
        apigateway = boto3.client('apigateway', region_name=region)
        
        print(f"🔧 Configuring CORS for API Gateway: {api_id}")
        print(f"📋 Stage: {stage_name}")
        print(f"🌍 Region: {region}")
        
        # Get all resources
        resources = apigateway.get_resources(restApiId=api_id)
        
        # CORS configuration
        cors_config = {
            "allowCredentials": True,
            "allowHeaders": [
                "Content-Type",
                "Authorization", 
                "X-Requested-With",
                "Accept",
                "Origin"
            ],
            "allowMethods": [
                "GET",
                "POST", 
                "PUT",
                "DELETE",
                "OPTIONS"
            ],
            "allowOrigins": [
                "*"
            ],
            "maxAge": 86400
        }
        
        # Apply CORS to all resources
        for resource in resources['items']:
            resource_id = resource['id']
            resource_path = resource['path']
            
            print(f"📝 Configuring CORS for resource: {resource_path} (ID: {resource_id})")
            
            try:
                # Enable CORS for the resource
                apigateway.put_method(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    authorizationType='NONE'
                )
                
                # Configure CORS response
                apigateway.put_method_response(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    statusCode='200',
                    responseParameters={
                        'method.response.header.Access-Control-Allow-Origin': True,
                        'method.response.header.Access-Control-Allow-Headers': True,
                        'method.response.header.Access-Control-Allow-Methods': True,
                        'method.response.header.Access-Control-Allow-Credentials': True,
                        'method.response.header.Access-Control-Max-Age': True
                    }
                )
                
                # Create integration for OPTIONS
                apigateway.put_integration(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    type='MOCK',
                    requestTemplates={
                        'application/json': '{"statusCode": 200}'
                    }
                )
                
                # Configure integration response
                apigateway.put_integration_response(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    statusCode='200',
                    responseParameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'",
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,X-Requested-With,Accept,Origin'",
                        'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                        'method.response.header.Access-Control-Allow-Credentials': "'true'",
                        'method.response.header.Access-Control-Max-Age': "'86400'"
                    }
                )
                
                print(f"✅ CORS configured for {resource_path}")
                
            except Exception as e:
                print(f"⚠️ Could not configure CORS for {resource_path}: {e}")
                continue
        
        # Deploy the changes
        print("🚀 Deploying API Gateway changes...")
        apigateway.create_deployment(
            restApiId=api_id,
            stageName=stage_name,
            description='CORS configuration deployment'
        )
        
        print("✅ API Gateway CORS configuration completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error configuring API Gateway CORS: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python configure_api_cors.py <API_GATEWAY_ID> [STAGE_NAME] [REGION]")
        print("Example: python configure_api_cors.py a1kn0j91k8 prod ap-south-1")
        sys.exit(1)
    
    api_id = sys.argv[1]
    stage_name = sys.argv[2] if len(sys.argv) > 2 else 'prod'
    region = sys.argv[3] if len(sys.argv) > 3 else 'ap-south-1'
    
    success = configure_api_gateway_cors(api_id, stage_name, region)
    
    if success:
        print("\n🎉 CORS configuration completed successfully!")
        print("Your frontend should now be able to make requests to the API.")
    else:
        print("\n❌ CORS configuration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
