#!/bin/bash

# WebSocket API Deployment Script
# This script deploys the WebSocket API for real-time chat

set -e

echo "🚀 Starting WebSocket API deployment..."

# Configuration
STACK_NAME="knowledgebot-websocket"
REGION="us-east-1"
STAGE="prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    print_error "SAM CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
print_status "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "AWS credentials configured"

# Create deployment package for WebSocket Lambda
print_status "Creating deployment package for WebSocket Lambda..."

# Create a temporary directory for the deployment package
TEMP_DIR=$(mktemp -d)
cp microservices/chat-orchestrator-websocket.py "$TEMP_DIR/"
cp requirements-zip-lambdas.txt "$TEMP_DIR/requirements.txt"

# Install dependencies
print_status "Installing Python dependencies..."
cd "$TEMP_DIR"
pip install -r requirements.txt -t .

# Create ZIP file
print_status "Creating ZIP package..."
zip -r chat-orchestrator-websocket.zip . -x "*.pyc" "__pycache__/*" "*.git*"

# Move back to project directory
cd - > /dev/null

print_success "Deployment package created"

# Deploy using SAM
print_status "Deploying WebSocket API using SAM..."

sam deploy \
    --template-file websocket-deployment.yml \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides StageName="$STAGE" \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    print_success "WebSocket API deployed successfully!"
else
    print_error "WebSocket API deployment failed!"
    exit 1
fi

# Get WebSocket API URL
print_status "Getting WebSocket API URL..."
WEBSOCKET_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiUrl`].OutputValue' \
    --output text)

if [ -n "$WEBSOCKET_URL" ]; then
    print_success "WebSocket API URL: $WEBSOCKET_URL"
    
    # Update the client example with the actual URL
    if [ -f "websocket-client-example.html" ]; then
        print_status "Updating client example with WebSocket URL..."
        sed -i.bak "s|wss://YOUR_API_GATEWAY_ID.execute-api.us-east-1.amazonaws.com/prod|$WEBSOCKET_URL|g" websocket-client-example.html
        rm websocket-client-example.html.bak
        print_success "Client example updated"
    fi
else
    print_warning "Could not retrieve WebSocket API URL"
fi

# Get WebSocket API ID
print_status "Getting WebSocket API ID..."
WEBSOCKET_API_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiId`].OutputValue' \
    --output text)

if [ -n "$WEBSOCKET_API_ID" ]; then
    print_success "WebSocket API ID: $WEBSOCKET_API_ID"
else
    print_warning "Could not retrieve WebSocket API ID"
fi

# Clean up temporary directory
rm -rf "$TEMP_DIR"

print_success "WebSocket API deployment completed!"
print_status "Next steps:"
print_status "1. Test the WebSocket connection using the client example"
print_status "2. Update your frontend to use the WebSocket URL: $WEBSOCKET_URL"
print_status "3. Monitor the Lambda logs for any issues"

echo ""
print_status "WebSocket API Details:"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $REGION"
echo "  Stage: $STAGE"
echo "  WebSocket URL: $WEBSOCKET_URL"
echo "  API ID: $WEBSOCKET_API_ID"
echo ""
print_status "To test the WebSocket API:"
echo "  1. Open websocket-client-example.html in your browser"
echo "  2. The WebSocket URL should be automatically configured"
echo "  3. Start chatting!"
