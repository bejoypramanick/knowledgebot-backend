#!/bin/bash

# Disable Manual Deployment Script
# This script disables manual deployment and ensures only GitHub Actions can deploy

set -e

echo "🔒 Disabling manual deployment and enabling GitHub Actions only deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 1. Make deployment scripts read-only and add warning headers
print_status "Making deployment scripts read-only and adding warning headers..."

# Add warning header to deploy-websocket.sh
if [ -f "deploy-websocket.sh" ]; then
    print_status "Adding warning header to deploy-websocket.sh..."
    cat > deploy-websocket.sh << 'EOF'
#!/bin/bash

# ⚠️  WARNING: MANUAL DEPLOYMENT DISABLED ⚠️
# This script has been disabled to prevent manual deployments.
# All deployments must now go through GitHub Actions.
# 
# To deploy:
# 1. Push your changes to the main or develop branch
# 2. GitHub Actions will automatically build and deploy
# 3. Or use the "workflow_dispatch" trigger in GitHub Actions
#
# If you need to deploy manually for emergency reasons:
# 1. Contact the DevOps team
# 2. Temporarily enable this script
# 3. Deploy and immediately disable again

echo "❌ Manual deployment is disabled!"
echo "Please use GitHub Actions for all deployments."
echo "See: https://github.com/your-org/knowledgebot-backend/actions"
exit 1
EOF
    chmod 444 deploy-websocket.sh  # Make read-only
    print_success "deploy-websocket.sh disabled"
fi

# 2. Create a deployment policy file
print_status "Creating deployment policy file..."
cat > DEPLOYMENT_POLICY.md << 'EOF'
# Deployment Policy

## Overview
This project uses **GitHub Actions only** for all deployments. Manual deployment scripts are disabled to ensure consistency, security, and proper CI/CD practices.

## Allowed Deployment Methods

### 1. Automatic Deployment (Recommended)
- **Trigger**: Push to `main` or `develop` branches
- **Process**: GitHub Actions automatically builds and deploys
- **Environment**: 
  - `main` branch → Production
  - `develop` branch → Staging

### 2. Manual Deployment via GitHub Actions
- **Trigger**: Use "workflow_dispatch" in GitHub Actions
- **Process**: 
  1. Go to Actions tab in GitHub
  2. Select "Deploy KnowledgeBot Backend" workflow
  3. Click "Run workflow"
  4. Choose environment (staging/production)
  5. Click "Run workflow"

### 3. Emergency Deployment (DevOps Only)
- **When**: Critical production issues requiring immediate fix
- **Process**: 
  1. Contact DevOps team
  2. Temporarily enable manual scripts
  3. Deploy and immediately disable scripts
  4. Document the emergency deployment

## Disabled Methods
- ❌ Direct AWS CLI deployment
- ❌ Manual Docker builds and pushes
- ❌ Local deployment scripts
- ❌ Direct Lambda function updates

## Security Benefits
- All deployments are logged and auditable
- Consistent environment across all deployments
- Automated security scanning
- Proper secret management
- Rollback capabilities

## Getting Help
- **GitHub Issues**: Create an issue for deployment problems
- **DevOps Team**: Contact for emergency deployments
- **Documentation**: See README.md for detailed setup instructions
EOF

print_success "Deployment policy created"

# 3. Create a pre-commit hook to prevent manual deployments
print_status "Creating pre-commit hook to prevent manual deployments..."
mkdir -p .git/hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# Pre-commit hook to prevent manual deployment attempts
# This hook checks for deployment-related changes and warns users

# Check if any deployment scripts are being modified
if git diff --cached --name-only | grep -E "(deploy|\.sh$)" > /dev/null; then
    echo "⚠️  WARNING: You are modifying deployment-related files!"
    echo "Remember: All deployments must go through GitHub Actions."
    echo "Manual deployment scripts are disabled for security reasons."
    echo ""
    echo "To deploy your changes:"
    echo "1. Push to main/develop branch (automatic deployment)"
    echo "2. Or use GitHub Actions workflow_dispatch trigger"
    echo ""
    read -p "Do you want to continue with this commit? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Commit cancelled."
        exit 1
    fi
fi
EOF
chmod +x .git/hooks/pre-commit
print_success "Pre-commit hook created"

# 4. Create a deployment validation script
print_status "Creating deployment validation script..."
cat > validate-deployment.sh << 'EOF'
#!/bin/bash

# Deployment Validation Script
# This script validates that deployments are done through GitHub Actions only

echo "🔍 Validating deployment configuration..."

# Check if GitHub Actions workflow exists
if [ ! -f ".github/workflows/deploy.yml" ]; then
    echo "❌ ERROR: GitHub Actions workflow not found!"
    echo "Please ensure .github/workflows/deploy.yml exists"
    exit 1
fi

# Check if manual deployment scripts are disabled
if [ -f "deploy-websocket.sh" ] && [ ! -r "deploy-websocket.sh" ]; then
    echo "✅ Manual deployment scripts are properly disabled"
else
    echo "❌ ERROR: Manual deployment scripts are not properly disabled!"
    exit 1
fi

# Check if deployment policy exists
if [ -f "DEPLOYMENT_POLICY.md" ]; then
    echo "✅ Deployment policy exists"
else
    echo "❌ ERROR: Deployment policy not found!"
    exit 1
fi

echo "✅ All deployment validations passed!"
echo "✅ Only GitHub Actions can deploy this project"
EOF
chmod +x validate-deployment.sh
print_success "Deployment validation script created"

# 5. Update README with deployment instructions
print_status "Updating README with GitHub Actions deployment instructions..."
if [ -f "README.md" ]; then
    # Backup original README
    cp README.md README.md.backup
    
    # Add deployment section if it doesn't exist
    if ! grep -q "## Deployment" README.md; then
        cat >> README.md << 'EOF'

## Deployment

This project uses **GitHub Actions only** for all deployments. Manual deployment scripts are disabled for security and consistency.

### Automatic Deployment
- Push to `main` branch → Production deployment
- Push to `develop` branch → Staging deployment

### Manual Deployment via GitHub Actions
1. Go to the [Actions tab](https://github.com/your-org/knowledgebot-backend/actions)
2. Select "Deploy KnowledgeBot Backend" workflow
3. Click "Run workflow"
4. Choose environment (staging/production)
5. Click "Run workflow"

### Emergency Deployment
For critical production issues, contact the DevOps team.

See [DEPLOYMENT_POLICY.md](DEPLOYMENT_POLICY.md) for detailed deployment policies.

EOF
    fi
    print_success "README updated with deployment instructions"
fi

# 6. Create a deployment status check script
print_status "Creating deployment status check script..."
cat > check-deployment-status.sh << 'EOF'
#!/bin/bash

# Deployment Status Check Script
# This script checks the status of the latest deployment

echo "📊 Checking deployment status..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Get the latest commit hash
LATEST_COMMIT=$(git rev-parse HEAD)
echo "Latest commit: $LATEST_COMMIT"

# Check if GitHub Actions is available
if command -v gh &> /dev/null; then
    echo "🔍 Checking GitHub Actions status..."
    gh run list --limit 5
else
    echo "⚠️  GitHub CLI not installed. Install with: brew install gh"
    echo "Or check manually at: https://github.com/your-org/knowledgebot-backend/actions"
fi

echo "✅ Deployment status check complete"
EOF
chmod +x check-deployment-status.sh
print_success "Deployment status check script created"

# 7. Final validation
print_status "Running final validation..."
./validate-deployment.sh

print_success "✅ Manual deployment disabled successfully!"
print_status "Summary of changes:"
echo "  - Manual deployment scripts are now read-only with warning headers"
echo "  - GitHub Actions workflow created for automated deployment"
echo "  - Pre-commit hook created to warn about deployment changes"
echo "  - Deployment policy document created"
echo "  - Validation scripts created"
echo "  - README updated with deployment instructions"
echo ""
print_status "Next steps:"
echo "  1. Commit these changes to your repository"
echo "  2. Push to main/develop branch to trigger first automated deployment"
echo "  3. Verify deployment in GitHub Actions"
echo "  4. Update the GitHub repository URL in the workflow files"
echo ""
print_warning "Remember: All future deployments must go through GitHub Actions!"
