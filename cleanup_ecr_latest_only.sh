#!/bin/bash

# ECR Image Cleanup Script - Keep Only Latest Image
# This script keeps only the latest image in each ECR repository

REGION="ap-south-1"

echo "🧹 Starting ECR image cleanup (keeping only latest image)..."

# Function to cleanup a repository
cleanup_repo() {
    local repo_name=$1
    echo ""
    echo "📦 Processing repository: $repo_name"
    
    # Get total count
    local total=$(aws ecr list-images --repository-name "$repo_name" --region "$REGION" --query 'length(imageIds)' --output text)
    echo "   📊 Total images found: $total"
    
    if [ "$total" -eq 0 ]; then
        echo "   ✅ Repository is empty, skipping..."
        return
    fi
    
    if [ "$total" -eq 1 ]; then
        echo "   ✅ Repository has only 1 image, keeping it..."
        return
    fi
    
    echo "   🗑️  Deleting old images (keeping only latest 1)..."
    
    # Get all image digests sorted by push time (newest first)
    local old_images=$(aws ecr describe-images --repository-name "$repo_name" --region "$REGION" \
        --query 'sort_by(imageDetails, &imagePushedAt) | reverse(@) | [1:].imageDigest' \
        --output text)
    
    # Delete each old image individually
    local count=0
    for digest in $old_images; do
        if [ -n "$digest" ]; then
            echo "      Deleting: $digest"
            aws ecr batch-delete-image --repository-name "$repo_name" \
                --image-ids imageDigest="$digest" --region "$REGION" \
                --query 'imageIds[0].imageDigest' --output text > /dev/null
            ((count++))
        fi
    done
    
    echo "   ✅ Deleted $count old images from $repo_name"
}

# Cleanup each repository
cleanup_repo "knowledgebot-backend"
cleanup_repo "knowledgebot-backend-core"
cleanup_repo "knowledgebot-backend-docling"
cleanup_repo "knowledgebot-backend-final"

echo ""
echo "🎉 ECR image cleanup completed!"
echo ""
echo "📊 Final repository status (keeping only latest image):"
echo "   knowledgebot-backend: $(aws ecr list-images --repository-name "knowledgebot-backend" --region "$REGION" --query 'length(imageIds)' --output text) images"
echo "   knowledgebot-backend-core: $(aws ecr list-images --repository-name "knowledgebot-backend-core" --region "$REGION" --query 'length(imageIds)' --output text) images"
echo "   knowledgebot-backend-docling: $(aws ecr list-images --repository-name "knowledgebot-backend-docling" --region "$REGION" --query 'length(imageIds)' --output text) images"
echo "   knowledgebot-backend-final: $(aws ecr list-images --repository-name "knowledgebot-backend-final" --region "$REGION" --query 'length(imageIds)' --output text) images"
