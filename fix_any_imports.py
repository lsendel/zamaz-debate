#!/usr/bin/env python3
"""Fix missing 'Any' imports in repository files"""

import re
from pathlib import Path

def fix_any_imports(file_path):
    """Add Any to typing imports if it's used but not imported"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if Any is used in the file
    if 'Any' not in content:
        return False
    
    # Check if Any is already imported
    if re.search(r'from typing import.*\bAny\b', content):
        return False
    
    # Find the typing import line
    import_match = re.search(r'(from typing import )([^\n]+)', content)
    if not import_match:
        return False
    
    # Add Any to the imports
    old_import = import_match.group(0)
    imports = import_match.group(2).strip()
    
    # Parse the imports
    import_list = [i.strip() for i in imports.split(',')]
    if 'Any' not in import_list:
        import_list.insert(0, 'Any')  # Add at the beginning
        new_import = f"{import_match.group(1)}{', '.join(import_list)}"
        
        # Replace in content
        new_content = content.replace(old_import, new_import)
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print(f"Fixed: {file_path}")
        return True
    
    return False

# Find all repository files in contexts
repo_files = []
contexts_dir = Path("src/contexts")
for context_dir in contexts_dir.glob("*"):
    if context_dir.is_dir():
        # Check repositories.py
        repo_file = context_dir / "repositories.py"
        if repo_file.exists():
            repo_files.append(repo_file)
        
        # Check domain_services.py
        services_file = context_dir / "domain_services.py" 
        if services_file.exists():
            repo_files.append(services_file)

print(f"Found {len(repo_files)} files to check")

fixed_count = 0
for file_path in repo_files:
    if fix_any_imports(file_path):
        fixed_count += 1

print(f"\nFixed {fixed_count} files")