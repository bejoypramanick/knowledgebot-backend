#!/bin/bash

# Build and push microservices to ECR
set -e

# Configuration
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Lambda services
SERVICES=(
    "action-executor"
    "chat-handler" 
    "claude-decision"
    "conversation-manager"
    "document-content"
    "document-management"
    "document-metadata"
    "embedding-service"
    "orchestrator"
    "rag-processor"
    "rag-search"
    "response-enhancement"
    "response-formatter"
    "source-extractor"
    "vector-search"
)

echo "Building and pushing microservices to ECR..."

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Create ECR repositories and build/push each service
for service in "${SERVICES[@]}"; do
    echo "Processing service: ${service}"
    
    # Create ECR repository if it doesn't exist
    echo "Creating ECR repository for ${service}..."
    aws ecr describe-repositories --repository-names "chatbot-${service}" --region ${AWS_REGION} > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name "chatbot-${service}" --region ${AWS_REGION}
    
    # Build Docker image
    echo "Building Docker image for ${service}..."
    cd "lambda/${service}"
    docker build -t "chatbot-${service}" .
    
    # Tag image for ECR
    docker tag "chatbot-${service}:latest" "${ECR_REGISTRY}/chatbot-${service}:latest"
    
    # Push image to ECR
    echo "Pushing image to ECR for ${service}..."
    docker push "${ECR_REGISTRY}/chatbot-${service}:latest"
    
    # Clean up local image
    docker rmi "chatbot-${service}:latest" "${ECR_REGISTRY}/chatbot-${service}:latest"
    
    cd ../..
    echo "Completed ${service}"
done

echo "All microservices built and pushed successfully!"
echo "ECR Registry: ${ECR_REGISTRY}"
echo "Services: ${SERVICES[*]}"
