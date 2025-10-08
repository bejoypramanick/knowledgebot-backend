#!/bin/bash

echo "🏗️ Building and pushing base images with resume capability..."

# Initialize build state file
BUILD_STATE_FILE="build_state.json"
if [ ! -f "$BUILD_STATE_FILE" ]; then
    echo '{"completed_images": [], "failed_images": []}' > "$BUILD_STATE_FILE"
fi

# Load state
COMPLETED_IMAGES=$(jq -r '.completed_images[]' "$BUILD_STATE_FILE" 2>/dev/null || echo "")
FAILED_IMAGES=$(jq -r '.failed_images[]' "$BUILD_STATE_FILE" 2>/dev/null || echo "")

# Create ECR repositories for base images
for base_image in docling docling-ocr docling-core docling-tables sentence-transformers embeddings-light; do
  echo "📋 Ensuring ECR repository exists for chatbot-base-$base_image..."
  if aws ecr describe-repositories --repository-names "chatbot-base-$base_image" --region ap-south-1 > /dev/null 2>&1; then
    echo "Repository chatbot-base-$base_image already exists"
  else
    echo "Creating repository chatbot-base-$base_image..."
    aws ecr create-repository --repository-name "chatbot-base-$base_image" --region ap-south-1
    
    # Set ECR repository policy
    aws ecr set-repository-policy \
      --repository-name "chatbot-base-$base_image" \
      --region ap-south-1 \
      --policy-text '{
          "Version": "2012-10-17",
          "Statement": [
              {
                  "Sid": "LambdaECRImageRetrievalPolicy",
                  "Effect": "Allow",
                  "Principal": {
                      "Service": "lambda.amazonaws.com"
                  },
                  "Action": [
                      "ecr:BatchGetImage",
                      "ecr:GetDownloadUrlForLayer"
                  ]
              }
          ]
      }' || echo "Policy already set"
  fi
done

# Build and push base images
cd backend/base-images

# Build specialized base images - always build if they don't exist or if there are changes
BUILD_DOCLING=""
BUILD_DOCLING_OCR=""
BUILD_DOCLING_CORE=""
BUILD_DOCLING_TABLES=""
BUILD_SENTENCE_TRANSFORMERS=""
BUILD_EMBEDDINGS_LIGHT=""

# Check if base images exist in ECR
if ! aws ecr describe-images --repository-name chatbot-base-docling --image-ids imageTag=latest --region ap-south-1 > /dev/null 2>&1; then
  echo "📦 Docling base image doesn't exist, building it..."
  BUILD_DOCLING="true"
fi

if ! aws ecr describe-images --repository-name chatbot-base-docling-ocr --image-ids imageTag=latest --region ap-south-1 > /dev/null 2>&1; then
  echo "📦 Docling OCR base image doesn't exist, building it..."
  BUILD_DOCLING_OCR="true"
fi

if ! aws ecr describe-images --repository-name chatbot-base-docling-core --image-ids imageTag=latest --region ap-south-1 > /dev/null 2>&1; then
  echo "📦 Docling Core base image doesn't exist, building it..."
  BUILD_DOCLING_CORE="true"
fi

if ! aws ecr describe-images --repository-name chatbot-base-docling-tables --image-ids imageTag=latest --region ap-south-1 > /dev/null 2>&1; then
  echo "📦 Docling Tables base image doesn't exist, building it..."
  BUILD_DOCLING_TABLES="true"
fi

if ! aws ecr describe-images --repository-name chatbot-base-sentence-transformers --image-ids imageTag=latest --region ap-south-1 > /dev/null 2>&1; then
  echo "📦 Sentence-transformers base image doesn't exist, building it..."
  BUILD_SENTENCE_TRANSFORMERS="true"
fi

if ! aws ecr describe-images --repository-name chatbot-base-embeddings-light --image-ids imageTag=latest --region ap-south-1 > /dev/null 2>&1; then
  echo "📦 Embeddings Light base image doesn't exist, building it..."
  BUILD_EMBEDDINGS_LIGHT="true"
fi

# Function to build image with memory management and resume capability
build_image() {
    local image_name=$1
    local dockerfile=$2
    local ecr_repo=$3
    
    # Check if this image was already completed
    if echo "$COMPLETED_IMAGES" | grep -q "$image_name"; then
      echo "⏭️ $image_name already completed, skipping..."
      return 0
    fi
    
    # Check if this image previously failed
    if echo "$FAILED_IMAGES" | grep -q "$image_name"; then
      echo "🔄 Retrying previously failed image: $image_name"
    else
      echo "🔨 Building $image_name..."
    fi
    
    # Monitor memory before build
    echo "📊 Memory before build:"
    if command -v free >/dev/null 2>&1; then
        free -h
    else
        echo "Memory monitoring not available on this system"
    fi
    
    # Build with memory limits and retry logic
    local retry_count=0
    local max_retries=3
    
    while [ $retry_count -lt $max_retries ]; do
      if docker build --memory=4g --memory-swap=6g -f "$dockerfile" -t "$image_name:latest" . 2>&1 | tee build.log; then
        # Verify the image was actually created
        if docker images "$image_name:latest" --format "{{.Repository}}:{{.Tag}}" | grep -q "$image_name:latest"; then
          echo "✅ Build successful for $image_name"
          break
        else
          echo "❌ Build reported success but image not found"
          retry_count=$((retry_count + 1))
          continue
        fi
      else
        retry_count=$((retry_count + 1))
        echo "❌ Build failed for $image_name (attempt $retry_count/$max_retries)"
        
        # Check if it's a space/OOM error
        if grep -q "No space left on device\|out of memory\|OOM\|ENOSPC" build.log; then
          echo "🚨 Space/OOM error detected, performing aggressive cleanup..."
          
          # Aggressive cleanup for space/OOM issues
          docker system prune -af --volumes || true
          docker builder prune -af || true
          docker image prune -af || true
          docker container prune -f || true
          docker volume prune -f || true
          docker network prune -f || true
          
          # Clean up system caches
          if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get clean || true
            sudo rm -rf /var/lib/apt/lists/* || true
          fi
          sudo rm -rf /tmp/* || true
          sudo rm -rf /var/tmp/* || true
          rm -rf ~/.cache/pip || true
          rm -rf /tmp/pip-* || true
          
          # Clean up logs
          sudo find /var/log -name "*.log" -type f -delete || true
          if command -v journalctl >/dev/null 2>&1; then
            sudo journalctl --vacuum-time=1d || true
          fi
          
          echo "📊 Space after aggressive cleanup:"
          df -h
          docker system df
          
          sleep 15
        else
          echo "🧹 Regular cleanup and retrying..."
          docker system prune -f || true
          docker builder prune -f || true
          sleep 10
        fi
        
        if [ $retry_count -ge $max_retries ]; then
          echo "💥 Build failed after $max_retries attempts"
          # Mark as failed in state file
          echo "📝 Marking $image_name as failed..."
          jq --arg img "$image_name" '.failed_images += [$img] | .completed_images -= [$img]' "$BUILD_STATE_FILE" > "${BUILD_STATE_FILE}.tmp" && mv "${BUILD_STATE_FILE}.tmp" "$BUILD_STATE_FILE"
          return 1
        fi
      fi
    done
    
    # Tag and push
    docker tag "$image_name:latest" "090163643302.dkr.ecr.ap-south-1.amazonaws.com/$ecr_repo:latest"
    docker push "090163643302.dkr.ecr.ap-south-1.amazonaws.com/$ecr_repo:latest"
    
    # Clean up local images
    docker rmi "$image_name:latest" "090163643302.dkr.ecr.ap-south-1.amazonaws.com/$ecr_repo:latest" || true
    
    # Mark as completed in state file
    echo "📝 Marking $image_name as completed..."
    jq --arg img "$image_name" '.completed_images += [$img] | .failed_images -= [$img]' "$BUILD_STATE_FILE" > "${BUILD_STATE_FILE}.tmp" && mv "${BUILD_STATE_FILE}.tmp" "$BUILD_STATE_FILE"
    
    # Basic cleanup after each build
    echo "🧹 Basic cleanup after $image_name build..."
    docker system prune -f || true
    docker builder prune -f || true
    
    # Show space after cleanup
    echo "📊 Space after cleanup:"
    df -h
    docker system df
    
    echo "✅ $image_name built and pushed successfully!"
}

# Build docling base image if needed
if [ "$BUILD_DOCLING" = "true" ]; then
  build_image "chatbot-base-docling" "Dockerfile.docling" "chatbot-base-docling"
else
  echo "⏭️ Docling base image already exists, skipping build"
fi

# Build docling OCR base image if needed
if [ "$BUILD_DOCLING_OCR" = "true" ]; then
  build_image "chatbot-base-docling-ocr" "Dockerfile.docling-ocr" "chatbot-base-docling-ocr"
else
  echo "⏭️ Docling OCR base image already exists, skipping build"
fi

# Build docling core base image if needed
if [ "$BUILD_DOCLING_CORE" = "true" ]; then
  build_image "chatbot-base-docling-core" "Dockerfile.docling-core" "chatbot-base-docling-core"
else
  echo "⏭️ Docling Core base image already exists, skipping build"
fi

# Build docling tables base image if needed
if [ "$BUILD_DOCLING_TABLES" = "true" ]; then
  build_image "chatbot-base-docling-tables" "Dockerfile.docling-tables" "chatbot-base-docling-tables"
else
  echo "⏭️ Docling Tables base image already exists, skipping build"
fi

# Build sentence-transformers base image if needed
if [ "$BUILD_SENTENCE_TRANSFORMERS" = "true" ]; then
  build_image "chatbot-base-sentence-transformers" "Dockerfile.sentence-transformers" "chatbot-base-sentence-transformers"
else
  echo "⏭️ Sentence-transformers base image already exists, skipping build"
fi

# Build embeddings light base image if needed
if [ "$BUILD_EMBEDDINGS_LIGHT" = "true" ]; then
  build_image "chatbot-base-embeddings-light" "Dockerfile.embeddings-light" "chatbot-base-embeddings-light"
else
  echo "⏭️ Embeddings Light base image already exists, skipping build"
fi

echo "🎉 Base images build completed!"

# Upload build state as artifact
echo "📤 Uploading build state..."
echo "Final build state:"
if [ -f "$BUILD_STATE_FILE" ]; then
    cat "$BUILD_STATE_FILE"
else
    echo "No build state file found"
fi

# Create artifact directory
mkdir -p artifacts
if [ -f "$BUILD_STATE_FILE" ]; then
    cp "$BUILD_STATE_FILE" artifacts/
    echo "Build state uploaded to artifacts/"
else
    echo "No build state file to upload"
fi

echo "✅ Script completed successfully!"
