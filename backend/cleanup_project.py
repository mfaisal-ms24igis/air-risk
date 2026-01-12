#!/usr/bin/env python
"""
Project Cleanup Script - Service-Oriented Refactoring
=====================================================

This script reorganizes the project by moving deprecated scripts 
into a dedicated folder to establish a clean, scalable architecture.

Author: Principal Software Architect
Date: December 11, 2025
"""

import os
import shutil
from pathlib import Path
from typing import List, Set
import sys


# Files/folders to preserve in root directory
PROTECTED_ROOT_ITEMS: Set[str] = {
    'manage.py',
    'cleanup_project.py',
    'requirements',
    '.env',
    '.env.example',
    '.env.docker.backup',
    '.gitignore',
    'README.md',
    'docker-compose.yml',
    'Dockerfile',
    # Directories to keep
    'air_risk',
    'air_quality',
    'correction',
    'exposure',
    'users',
    'frontend',
    'data',
    'media',
    'staticfiles',
    'geoserver',
    # Backup directories (will handle separately)
    'backups',
    'backup_20251204_203011',
    # Hidden directories
    '.git',
    '.vscode',
    '.pytest_cache',
    '.ruff_cache',
    '__pycache__',
    # Service account (sensitive)
    'gee-service-account.json',
}


def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.resolve()


def create_deprecated_folder(root: Path) -> Path:
    """
    Create the deprecated/ directory for old scripts.
    
    Args:
        root: Project root path
        
    Returns:
        Path to deprecated directory
    """
    deprecated_dir = root / 'deprecated'
    deprecated_dir.mkdir(exist_ok=True)
    
    # Create subdirectories for organization
    (deprecated_dir / 'scripts').mkdir(exist_ok=True)
    (deprecated_dir / 'tests').mkdir(exist_ok=True)
    (deprecated_dir / 'documentation').mkdir(exist_ok=True)
    
    print(f"✓ Created: {deprecated_dir}")
    return deprecated_dir


def identify_deprecated_files(root: Path) -> List[Path]:
    """
    Identify all loose Python scripts and test files that should be moved.
    
    Args:
        root: Project root path
        
    Returns:
        List of file paths to be moved
    """
    deprecated_files = []
    
    for item in root.iterdir():
        # Skip if it's in the protected list
        if item.name in PROTECTED_ROOT_ITEMS:
            continue
            
        # Skip directories
        if item.is_dir():
            continue
            
        # Identify deprecated scripts
        if item.suffix == '.py':
            deprecated_files.append(item)
        elif item.suffix in ['.html', '.md', '.csv', '.log', '.ps1', '.msi']:
            # Include helper files, test HTML, logs, PowerShell scripts
            deprecated_files.append(item)
    
    return deprecated_files


def categorize_file(file_path: Path) -> str:
    """
    Determine which subdirectory a file should go into.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Subdirectory name (scripts, tests, or documentation)
    """
    name = file_path.name.lower()
    
    if name.startswith('test_') or 'test' in name:
        return 'tests'
    elif file_path.suffix in ['.md', '.html']:
        return 'documentation'
    else:
        return 'scripts'


def move_files_to_deprecated(files: List[Path], deprecated_dir: Path, dry_run: bool = False) -> None:
    """
    Move files to the deprecated directory with categorization.
    
    Args:
        files: List of files to move
        deprecated_dir: Target deprecated directory
        dry_run: If True, only print actions without moving files
    """
    if not files:
        print("No files to move.")
        return
    
    print(f"\n{'DRY RUN - ' if dry_run else ''}Found {len(files)} file(s) to move:\n")
    
    moved_count = 0
    for file_path in files:
        category = categorize_file(file_path)
        target_dir = deprecated_dir / category
        target_path = target_dir / file_path.name
        
        # Handle name conflicts
        if target_path.exists():
            counter = 1
            stem = file_path.stem
            suffix = file_path.suffix
            while target_path.exists():
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        
        print(f"  {file_path.name} → deprecated/{category}/")
        
        if not dry_run:
            try:
                shutil.move(str(file_path), str(target_path))
                moved_count += 1
            except Exception as e:
                print(f"    ✗ Error moving {file_path.name}: {e}")
    
    if not dry_run:
        print(f"\n✓ Successfully moved {moved_count}/{len(files)} files")


def create_deprecated_readme(deprecated_dir: Path) -> None:
    """Create a README in the deprecated directory explaining its purpose."""
    readme_content = """# Deprecated Scripts & Files

This directory contains legacy scripts and files that have been moved out of the root directory as part of the Service-Oriented Architecture refactoring.

## Directory Structure

- **scripts/**: Standalone Python scripts (data collection, debugging, validation)
- **tests/**: Ad-hoc test files (not part of the formal test suite)
- **documentation/**: Old documentation files, API testers, and markdown files

## Status

These files are kept for reference but are **NOT part of the active codebase**. 

If you need functionality from any of these files:
1. Identify the relevant logic
2. Refactor it into the appropriate service module in `apps/`
3. Add proper tests in the formal test suite
4. Delete the deprecated file

## Migration Date

Moved to deprecated: December 11, 2025
Refactoring: Service-Oriented Architecture
"""
    
    readme_path = deprecated_dir / 'README.md'
    readme_path.write_text(readme_content, encoding='utf-8')
    print(f"✓ Created: {readme_path}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("PROJECT CLEANUP SCRIPT - Service-Oriented Refactoring")
    print("=" * 70)
    
    # Parse command-line arguments
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("\n⚠ DRY RUN MODE - No files will be moved\n")
    
    # Get project root
    root = get_project_root()
    print(f"\nProject Root: {root}\n")
    
    # Step 1: Create deprecated directory
    print("Step 1: Creating deprecated directory structure...")
    deprecated_dir = create_deprecated_folder(root)
    
    # Step 2: Identify files to move
    print("\nStep 2: Identifying deprecated files...")
    files_to_move = identify_deprecated_files(root)
    
    # Step 3: Move files
    print("\nStep 3: Moving files to deprecated/...")
    move_files_to_deprecated(files_to_move, deprecated_dir, dry_run)
    
    # Step 4: Create README
    if not dry_run:
        print("\nStep 4: Creating deprecated/README.md...")
        create_deprecated_readme(deprecated_dir)
    
    # Summary
    print("\n" + "=" * 70)
    if dry_run:
        print("DRY RUN COMPLETE - Run without --dry-run to execute")
    else:
        print("CLEANUP COMPLETE ✓")
        print(f"\nNext Steps:")
        print("  1. Review files in deprecated/ directory")
        print("  2. Run the refactoring script to create new structure")
        print("  3. Migrate business logic to service modules")
    print("=" * 70)


if __name__ == '__main__':
    main()
