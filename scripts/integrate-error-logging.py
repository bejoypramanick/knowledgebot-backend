#!/usr/bin/env python3
"""
Auto-integrate error logging with all Lambda functions
This script automatically adds error logging to all Lambda functions
"""

import os
import re
from pathlib import Path

def integrate_error_logging(file_path: str) -> bool:
    """Integrate error logging with a Lambda function"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if already integrated
        if 'from error_logger import' in content:
            print(f"✅ {file_path} already has error logging integrated")
            return True
        
        # Find the import section
        import_pattern = r'(import json\nimport os\nimport logging\nimport traceback\nimport sys\nfrom datetime import datetime)'
        
        if re.search(import_pattern, content):
            # Add error logging import
            new_imports = '''import json
import os
import logging
import traceback
import sys
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure'''
            
            content = re.sub(import_pattern, new_imports, content)
            
            # Find main exception handlers and add error logging
            # Pattern for main exception handler
            main_exception_pattern = r'(except Exception as e:\s*\n\s*logger\.error\(f"❌ Error.*?\)\s*\n\s*logger\.error\(f"📊 Stack trace:.*?\)\s*\n\s*return \{)'
            
            def add_error_logging(match):
                exception_block = match.group(1)
                
                # Extract function name from file path
                function_name = Path(file_path).stem
                
                # Add error logging before return
                error_logging = f'''        # Log error to centralized system
        log_error(
            '{function_name}',
            e,
            context,
            {{
                'event_keys': list(event.keys()) if event else [],
                'function_name': '{function_name}'
            }},
            'ERROR'
        )
        
        '''
                
                return exception_block.replace('return {', error_logging + 'return {')
            
            content = re.sub(main_exception_pattern, add_error_logging, content, flags=re.DOTALL)
            
            # Write back to file
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Integrated error logging with {file_path}")
            return True
        else:
            print(f"⚠️ Could not find standard import pattern in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error integrating {file_path}: {e}")
        return False

def main():
    """Main function to integrate error logging with all Lambda functions"""
    microservices_dir = Path('microservices')
    
    # Lambda functions to integrate (excluding error-logger and error-query)
    lambda_files = [
        'chat-orchestrator-business-logic.py',
        'chat-orchestrator-business-logic-optimized.py',
        'pinecone-library-handler.py',
        'neo4j-library-handler.py',
        'sentence-transformer-library-handler.py',
        'dynamodb-crud-handler.py',
        's3-unified-handler.py',
        'docling-library-handler.py',
        'document-processor-business-logic.py'
    ]
    
    print("🔧 Integrating error logging with Lambda functions...")
    print("=" * 60)
    
    success_count = 0
    total_count = len(lambda_files)
    
    for file_name in lambda_files:
        file_path = microservices_dir / file_name
        if file_path.exists():
            if integrate_error_logging(str(file_path)):
                success_count += 1
        else:
            print(f"⚠️ File not found: {file_path}")
    
    print("=" * 60)
    print(f"✅ Successfully integrated error logging with {success_count}/{total_count} Lambda functions")
    
    if success_count < total_count:
        print("⚠️ Some files may need manual integration")
        print("📝 Check the files above for any issues")

if __name__ == "__main__":
    main()
