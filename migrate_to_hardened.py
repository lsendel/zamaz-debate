#!/usr/bin/env python3
"""
Migration script to transition to the hardened Zamaz Debate System
Safely backs up existing configuration and migrates to new structure
"""
import os
import shutil
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def create_backup():
    """Create a backup of the current system"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backup_{timestamp}")
    
    print(f"📦 Creating backup in {backup_dir}...")
    backup_dir.mkdir(exist_ok=True)
    
    # Backup critical files
    files_to_backup = [
        "src/web/app.py",
        "services/pr_service.py",
        ".env",
        "requirements.txt",
        "data/"
    ]
    
    for item in files_to_backup:
        source = Path(item)
        if source.exists():
            dest = backup_dir / item
            if source.is_dir():
                shutil.copytree(source, dest, dirs_exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            print(f"  ✓ Backed up {item}")
    
    return backup_dir


def install_dependencies():
    """Install new dependencies"""
    print("\n📦 Installing new dependencies...")
    try:
        # First upgrade pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install new requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("  ✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to install dependencies: {e}")
        return False


def migrate_services():
    """Migrate to hardened services"""
    print("\n🔧 Migrating services...")
    
    migrations = [
        ("src/web/app.py", "src/web/app_original.py", "src/web/app_hardened.py"),
        ("services/pr_service.py", "services/pr_service_original.py", "services/pr_service_hardened.py")
    ]
    
    for current, backup, hardened in migrations:
        current_path = Path(current)
        backup_path = Path(backup)
        hardened_path = Path(hardened)
        
        if current_path.exists() and hardened_path.exists():
            # Backup original
            shutil.copy2(current_path, backup_path)
            # Replace with hardened version
            shutil.copy2(hardened_path, current_path)
            print(f"  ✓ Migrated {current}")
        else:
            print(f"  ⚠️  Skipped {current} (file not found)")


def update_imports():
    """Update imports in the nucleus to use new services"""
    print("\n🔧 Updating imports...")
    
    nucleus_file = Path("src/core/nucleus.py")
    if nucleus_file.exists():
        content = nucleus_file.read_text()
        
        # Add new imports if not present
        new_imports = [
            "from services.error_handling import with_retry, ErrorContext, AIServiceError",
            "from services.atomic_file_ops import atomic_ops",
            "from services.data_validation import DecisionValidated, EvolutionValidated"
        ]
        
        for imp in new_imports:
            if imp not in content:
                # Add after the last import
                lines = content.split('\n')
                import_end = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        import_end = i
                
                lines.insert(import_end + 1, imp)
                content = '\n'.join(lines)
        
        # Write back
        nucleus_file.write_text(content)
        print("  ✓ Updated nucleus imports")


def create_directories():
    """Create required directories"""
    print("\n📁 Creating directories...")
    
    dirs = [
        ".backups",
        "logs",
        "data/pr_drafts",
        "data/decisions",
        "data/debates",
        "data/evolutions"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {dir_path}")


def update_startup_script():
    """Update the startup script to use the hardened app"""
    print("\n🚀 Updating startup script...")
    
    script_content = """#!/bin/bash
# Zamaz Debate System - Hardened Startup Script

echo "🚀 Starting Zamaz Debate System (Hardened)..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the hardened web interface
echo "Starting web interface..."
python -m uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload --log-config logging.json

echo "✨ System started successfully!"
"""
    
    startup_file = Path("start_hardened.sh")
    startup_file.write_text(script_content)
    startup_file.chmod(0o755)
    print("  ✓ Created start_hardened.sh")


def create_logging_config():
    """Create logging configuration"""
    print("\n📝 Creating logging configuration...")
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "logs/zamaz_debate.log",
                "maxBytes": 10485760,
                "backupCount": 5
            }
        },
        "loggers": {
            "": {
                "level": "INFO",
                "handlers": ["console", "file"]
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }
    
    import json
    with open("logging.json", "w") as f:
        json.dump(logging_config, f, indent=2)
    
    print("  ✓ Created logging.json")


def run_tests():
    """Run basic tests to ensure system works"""
    print("\n🧪 Running basic tests...")
    
    # Test imports
    try:
        from services.security_utils import sanitize_git_branch_name
        from services.atomic_file_ops import AtomicFileOperations
        from services.error_handling import CircuitBreaker
        from services.data_validation import DecisionValidated
        print("  ✓ All new modules import successfully")
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    
    # Test security utilities
    try:
        from services.security_utils import sanitize_git_branch_name
        assert sanitize_git_branch_name("feature/test-123") == "feature/test-123"
        print("  ✓ Security utilities working")
    except Exception as e:
        print(f"  ❌ Security test failed: {e}")
    
    return True


def main():
    """Main migration process"""
    print("🛡️  Zamaz Debate System - Migration to Hardened Version")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src/core/nucleus.py").exists():
        print("❌ Error: Must run from project root directory")
        sys.exit(1)
    
    # Create backup
    backup_dir = create_backup()
    print(f"\n✅ Backup created: {backup_dir}")
    
    try:
        # Install dependencies
        if not install_dependencies():
            print("\n⚠️  Warning: Some dependencies failed to install")
            print("You may need to install them manually")
        
        # Create required directories
        create_directories()
        
        # Migrate services
        migrate_services()
        
        # Update imports
        update_imports()
        
        # Create startup script
        update_startup_script()
        
        # Create logging config
        create_logging_config()
        
        # Run tests
        if run_tests():
            print("\n✅ Migration completed successfully!")
            print("\n📝 Next steps:")
            print("1. Stop the current server (Ctrl+C)")
            print("2. Run: ./start_hardened.sh")
            print("3. Test the system at http://localhost:8000")
            print("4. Check health at http://localhost:8000/health")
        else:
            print("\n⚠️  Migration completed with warnings")
            print("Please check the logs and test thoroughly")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"Backup available at: {backup_dir}")
        sys.exit(1)


if __name__ == "__main__":
    main()