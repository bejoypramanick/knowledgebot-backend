#!/bin/bash
# ECR Lifecycle Policy Setup Script
# Applies lifecycle policies to all knowledgebot ECR repositories

set -e

AWS_REGION="ap-south-1"
ECR_REPOSITORY_PREFIX="knowledgebot"
LIFECYCLE_POLICY_FILE="ecr-lifecycle-policy.json"

echo "🔧 Setting up ECR lifecycle policies for automatic image cleanup"
echo "📍 Region: $AWS_REGION"
echo "📦 Repository prefix: $ECR_REPOSITORY_PREFIX"

# Check if lifecycle policy file exists
if [ ! -f "$LIFECYCLE_POLICY_FILE" ]; then
    echo "❌ Lifecycle policy file not found: $LIFECYCLE_POLICY_FILE"
    exit 1
fi

# List all ECR repositories with knowledgebot prefix
echo "🔍 Finding ECR repositories..."
REPOSITORIES=$(aws ecr describe-repositories \
    --region $AWS_REGION \
    --query "repositories[?starts_with(repositoryName, '$ECR_REPOSITORY_PREFIX')].repositoryName" \
    --output text)

if [ -z "$REPOSITORIES" ]; then
    echo "⚠️  No repositories found with prefix: $ECR_REPOSITORY_PREFIX"
    exit 0
fi

echo "📋 Found repositories:"
echo "$REPOSITORIES" | tr '\t' '\n' | while read repo; do
    echo "  - $repo"
done

# Apply lifecycle policy to each repository
echo ""
echo "🚀 Applying lifecycle policies..."

echo "$REPOSITORIES" | tr '\t' '\n' | while read repo; do
    echo "📦 Processing repository: $repo"
    
    # Apply lifecycle policy
    if aws ecr put-lifecycle-policy \
        --repository-name "$repo" \
        --lifecycle-policy-text "file://$LIFECYCLE_POLICY_FILE" \
        --region $AWS_REGION > /dev/null; then
        echo "  ✅ Lifecycle policy applied successfully"
    else
        echo "  ❌ Failed to apply lifecycle policy"
    fi
done

echo ""
echo "🎉 ECR lifecycle policy setup complete!"
echo ""
echo "📋 Policy Summary:"
echo "  • Keep latest 3 tagged images"
echo "  • Keep latest 2 untagged images" 
echo "  • Remove images older than 30 days"
echo "  • Automatic cleanup on new image upload"
echo ""
echo "💡 This will help manage storage costs and keep repositories clean"
