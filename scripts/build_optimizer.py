#!/usr/bin/env python3
"""
Intelligent Build Optimization for GitHub Actions
Only builds Docker images when related code has changed
"""

import os
import json
import subprocess
from typing import Dict, List, Set
from pathlib import Path

class BuildOptimizer:
    """Intelligent build optimization based on file changes"""
    
    # Service to file mapping
    SERVICE_FILE_MAPPING = {
        'docling-unified': [
            'microservices/docling-unified-handler.py',
            'requirements-docling-unified.txt',
            'Dockerfile.docling-unified'
        ],
        'agent-query': [
            'microservices/intelligent-agent-handler.py',
            'microservices/agent-query-handler.py',
            'requirements-intelligent-agent.txt',
            'Dockerfile.intelligent-agent'
        ],
        's3-unified': [
            'microservices/s3-unified-handler.py',
            'requirements-s3-unified.txt',
            'Dockerfile.s3-unified'
        ],
        'pinecone-unified': [
            'microservices/pinecone-unified-handler.py',
            'requirements-pinecone-unified.txt',
            'Dockerfile.pinecone-unified'
        ],
        'neo4j-unified': [
            'microservices/neo4j-unified-handler.py',
            'requirements-neo4j-unified.txt',
            'Dockerfile.neo4j-unified'
        ],
        'dynamodb-crud': [
            'microservices/dynamodb-crud-handler.py',
            'requirements-dynamodb-crud.txt',
            'Dockerfile.dynamodb-crud-layered'
        ],
        'chat-generator': [
            'microservices/chat-generator-handler.py',
            'requirements-chat-generator.txt',
            'Dockerfile.chat-generator-layered'
        ],
        'embedding-generator': [
            'microservices/embedding-generator-handler.py',
            'requirements-embedding-generator.txt',
            'Dockerfile.embedding-generator-layered'
        ]
    }
    
    # Shared dependencies that affect all services
    SHARED_DEPENDENCIES = [
        'utils/',
        'agent-toolkit/',
        '.github/workflows/',
        'requirements-base-layer.txt',
        'requirements-core-layer.txt',
        'requirements-ml-layer.txt',
        'requirements-database-layer.txt'
    ]
    
    @staticmethod
    def get_changed_files() -> Set[str]:
        """Get list of changed files from git"""
        try:
            # Get changed files from last commit
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            changed_files = set(result.stdout.strip().split('\n'))
            return {f for f in changed_files if f}  # Remove empty strings
        except subprocess.CalledProcessError:
            # Fallback: get all files if git command fails
            return set()
    
    @staticmethod
    def get_services_to_build(changed_files: Set[str]) -> Set[str]:
        """Determine which services need to be built based on changed files"""
        services_to_build = set()
        
        # Check if any shared dependencies changed
        shared_changed = any(
            any(f.startswith(dep) for dep in BuildOptimizer.SHARED_DEPENDENCIES)
            for f in changed_files
        )
        
        if shared_changed:
            # If shared dependencies changed, build all services
            return set(BuildOptimizer.SERVICE_FILE_MAPPING.keys())
        
        # Check each service's specific files
        for service, files in BuildOptimizer.SERVICE_FILE_MAPPING.items():
            if any(f in changed_files for f in files):
                services_to_build.add(service)
        
        return services_to_build
    
    @staticmethod
    def generate_build_matrix(services_to_build: Set[str]) -> Dict[str, List[Dict]]:
        """Generate GitHub Actions matrix for services that need building"""
        # Service configurations
        service_configs = {
            'docling-unified': {
                'dockerfile': 'Dockerfile.docling-unified',
                'requirements': 'requirements-docling-unified.txt',
                'size': '~2.5GB',
                'memory': 3008,
                'timeout': 900
            },
            'agent-query': {
                'dockerfile': 'Dockerfile.intelligent-agent',
                'requirements': 'requirements-intelligent-agent.txt',
                'size': '~200MB',
                'memory': 1024,
                'timeout': 300
            },
            's3-unified': {
                'dockerfile': 'Dockerfile.s3-unified',
                'requirements': 'requirements-s3-unified.txt',
                'size': '~85MB',
                'memory': 256,
                'timeout': 30
            },
            'pinecone-unified': {
                'dockerfile': 'Dockerfile.pinecone-unified',
                'requirements': 'requirements-pinecone-unified.txt',
                'size': '~155MB',
                'memory': 512,
                'timeout': 60
            },
            'neo4j-unified': {
                'dockerfile': 'Dockerfile.neo4j-unified',
                'requirements': 'requirements-neo4j-unified.txt',
                'size': '~155MB',
                'memory': 512,
                'timeout': 60
            },
            'dynamodb-crud': {
                'dockerfile': 'Dockerfile.dynamodb-crud-layered',
                'requirements': 'requirements-dynamodb-crud.txt',
                'size': '~85MB',
                'memory': 256,
                'timeout': 30
            },
            'chat-generator': {
                'dockerfile': 'Dockerfile.chat-generator-layered',
                'requirements': 'requirements-chat-generator.txt',
                'size': '~405MB',
                'memory': 1024,
                'timeout': 300
            },
            'embedding-generator': {
                'dockerfile': 'Dockerfile.embedding-generator-layered',
                'requirements': 'requirements-embedding-generator.txt',
                'size': '~405MB',
                'memory': 1024,
                'timeout': 120
            }
        }
        
        # Generate matrix
        matrix = []
        for service in services_to_build:
            if service in service_configs:
                config = service_configs[service]
                matrix.append({
                    'name': service,
                    'dockerfile': config['dockerfile'],
                    'requirements': config['requirements'],
                    'size': config['size'],
                    'memory': config['memory'],
                    'timeout': config['timeout']
                })
        
        return {'include': matrix}
    
    @staticmethod
    def should_skip_build() -> bool:
        """Check if build should be skipped entirely"""
        changed_files = BuildOptimizer.get_changed_files()
        
        # Skip build if only documentation or non-code files changed
        skip_patterns = [
            'README.md',
            '*.md',
            '.gitignore',
            '.github/workflows/deploy-unified-microservices.yml'  # Skip if only workflow changed
        ]
        
        # Check if all changed files match skip patterns
        for file in changed_files:
            if not any(file.startswith(pattern.replace('*', '')) or file.endswith(pattern.replace('*', '')) 
                     for pattern in skip_patterns):
                return False
        
        return len(changed_files) > 0

def main():
    """Main function for build optimization"""
    print("🔍 Analyzing changed files for intelligent build optimization...")
    
    changed_files = BuildOptimizer.get_changed_files()
    print(f"📝 Changed files: {len(changed_files)}")
    for file in sorted(changed_files):
        print(f"  - {file}")
    
    if BuildOptimizer.should_skip_build():
        print("⏭️  Skipping build - only documentation/non-code files changed")
        return
    
    services_to_build = BuildOptimizer.get_services_to_build(changed_files)
    print(f"🏗️  Services to build: {len(services_to_build)}")
    for service in sorted(services_to_build):
        print(f"  - {service}")
    
    if not services_to_build:
        print("⏭️  No services need building")
        return
    
    # Generate build matrix
    matrix = BuildOptimizer.generate_build_matrix(services_to_build)
    
    # Output matrix for GitHub Actions
    matrix_json = json.dumps(matrix, indent=2)
    print(f"📋 Build matrix:\n{matrix_json}")
    
    # Set GitHub Actions output
    if os.getenv('GITHUB_ACTIONS'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"build_matrix={matrix_json}\n")
            f.write(f"services_to_build={','.join(sorted(services_to_build))}\n")
            f.write(f"should_build={'true' if services_to_build else 'false'}\n")

if __name__ == "__main__":
    main()
