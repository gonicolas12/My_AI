#!/usr/bin/env python3
"""
AI Assistant Launcher - Main entry point for all interfaces
Provides easy access to CLI, GUI, and other interfaces.
"""
import sys
import os
import argparse
import subprocess
import asyncio
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from utils.logger import Logger


def setup_environment():
    """Setup the environment and check dependencies."""
    logger = Logger.get_logger("launcher")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check critical dependencies
    critical_deps = [
        'click', 'yaml', 'rich'
    ]
    
    # Optional but important dependencies
    optional_deps = [
        'transformers', 'torch', 'fitz', 'docx'
    ]
    
    missing_critical = []
    missing_optional = []
    
    for dep in critical_deps:
        try:
            if dep == 'yaml':
                import yaml
            else:
                __import__(dep)
        except ImportError:
            missing_critical.append(dep)
    
    for dep in optional_deps:
        try:
            if dep == 'fitz':
                import fitz
            elif dep == 'docx':
                import docx
            else:
                __import__(dep)
        except ImportError:
            missing_optional.append(dep)
    
    if missing_critical:
        print(f"❌ Missing critical dependencies: {', '.join(missing_critical)}")
        print("💡 Quick fix: pip install --user click pyyaml rich")
        return False
    
    print("✅ All critical dependencies available")
    
    if missing_optional:
        print(f"⚠️  Optional dependencies missing: {', '.join(missing_optional)}")
        print("💡 For full functionality: pip install --user -r requirements.txt")
    
    return True


def launch_cli(args):
    """Launch the CLI interface."""
    try:
        # OPTION 1: Utiliser le point d'entrée CLI spécifique
        from interfaces.cli import CLIInterface
        print("🚀 Launching CLI interface...")
        
        async def run_cli():
            cli = CLIInterface()
            await cli.run()
        
        asyncio.run(run_cli())
        
    except Exception as e:
        print(f"❌ Error launching CLI: {e}")
        return False
    return True


def launch_gui(args):
    """Launch the Modern GUI interface with fallback to standard GUI."""
    try:
        from interfaces.gui_modern import main as gui_main
        print("🚀 Launching Modern GUI interface (v3.0.0 - Style Claude)...")
        gui_main()
    except ImportError as e:
        print(f"❌ Error importing modern GUI: {e}")
        print("💡 Modern GUI requires: customtkinter, tkinterdnd2, pillow")
        print("💡 Install with: python install_gui_deps.py")
        print("💡 Falling back to standard GUI...")
        try:
            from interfaces.gui import main as gui_main
            print("🚀 Launching Standard GUI interface...")
            gui_main()
        except Exception as e2:
            print(f"❌ Error launching standard GUI: {e2}")
            print("💡 tkinter is included with Python - check if GUI dependencies are installed")
            print("💡 Try: python install_gui_deps.py")
            return False
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        print("💡 For modern interface, install: python install_gui_deps.py")
        return False
    return True


def launch_demo(args):
    """Launch the demo script."""
    try:
        # Import et lancement de la démo
        from demo import main as demo_main
        print("🚀 Launching demo...")
        
        # La fonction demo_main est asynchrone, l'exécuter avec asyncio
        asyncio.run(demo_main())
            
    except Exception as e:
        print(f"❌ Error launching demo: {e}")
        return False
    return True


def run_tests(args):
    """Run the test suite."""
    try:
        print("🧪 Running tests...")
        
        # Check if coverage is requested
        if '--coverage' in args:
            subprocess.run([sys.executable, 'run_tests.py', '--coverage'], check=True)
        else:
            subprocess.run([sys.executable, 'run_tests.py'], check=True)
        
        print("✅ Tests completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    return True


def install_dependencies(args):
    """Install project dependencies."""
    try:
        print("📦 Installing dependencies...")
        
        # Use install script if available
        if os.name == 'nt':  # Windows
            if os.path.exists('install.bat'):
                subprocess.run(['install.bat'], check=True, shell=True)
            else:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        else:  # Unix/Linux/macOS
            if os.path.exists('install.sh'):
                subprocess.run(['bash', 'install.sh'], check=True)
            else:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    return True


def show_status():
    """Show system status and configuration."""
    print("📊 System Status")
    print("=" * 50)
    
    # Python info
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Project: {project_root}")
    
    # Check AI engine status
    try:
        from core.ai_engine import AIEngine
        from core.config import Config
        
        config = Config()
        engine = AIEngine(config)
        
        print(f"⚙️  Configuration: {config.config_file}")
        print(f"🤖 LLM Provider: {config.get('llm.provider', 'Not configured')}")
        
        # Try to initialize AI
        if engine.initialize_llm():
            print("🟢 AI Engine: Ready")
        else:
            print("🟡 AI Engine: Not available")
            
    except Exception as e:
        print(f"🔴 AI Engine: Error - {e}")
    
    # Check available interfaces
    print("\\n🖥️  Available Interfaces:")
    
    # CLI
    try:
        from interfaces.cli import CLIInterface
        print("  ✅ CLI (Command Line)")
    except ImportError:
        print("  ❌ CLI (Command Line)")
    
    # GUI
    try:
        import tkinter
        print("  ✅ GUI (Graphical)")
    except ImportError:
        print("  ❌ GUI (Graphical) - tkinter not available")
    
    # Check examples
    examples_dir = project_root / "examples"
    if examples_dir.exists():
        examples = list(examples_dir.glob("*.py"))
        print(f"\\n📚 Examples available: {len(examples)}")
        for example in examples:
            print(f"  - {example.stem}")
    
    # Check tests
    tests_dir = project_root / "tests"
    if tests_dir.exists():
        test_files = list(tests_dir.glob("test_*.py"))
        print(f"\\n🧪 Test files: {len(test_files)}")
    
    print("\\n" + "=" * 50)


def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(
        description="🤖 My AI Personal Assistant Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py cli --help                 # CLI help
  python launcher.py gui                        # Launch GUI
  python launcher.py demo                       # Run demo
  python launcher.py test                       # Run tests
  python launcher.py test --coverage            # Run tests with coverage
  python launcher.py install                    # Install dependencies
  python launcher.py status                     # Show system status
  
  # CLI examples:
  python launcher.py cli chat "Hello, AI!"
  python launcher.py cli process-file document.pdf
  python launcher.py cli generate-function "calculate factorial"
        """
    )
    
    parser.add_argument(
        'interface', 
        choices=['cli', 'gui', 'demo', 'test', 'install', 'status'],
        help='Interface or action to launch'
    )
    
    parser.add_argument(
        'args', 
        nargs='*',
        help='Additional arguments for the interface'
    )
    
    parser.add_argument(
        '--skip-check', 
        action='store_true',
        help='Skip environment checks'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("🤖 My AI Personal Assistant v3.0.0")
    print("🎨 Interface Graphique Moderne - Style Claude")
    print("=" * 50)
    
    # Setup environment (unless skipped)
    if not args.skip_check:
        if not setup_environment():
            print("\\n💡 Use --skip-check to bypass environment checks")
            sys.exit(1)
        print()
    
    # Route to appropriate launcher
    success = True
    
    if args.interface == 'cli':
        success = launch_cli(args.args)
    elif args.interface == 'gui':
        success = launch_gui(args.args)
    elif args.interface == 'demo':
        success = launch_demo(args.args)
    elif args.interface == 'test':
        success = run_tests(args.args)
    elif args.interface == 'install':
        success = install_dependencies(args.args)
    elif args.interface == 'status':
        show_status()
    
    if not success:
        sys.exit(1)
    
    print("\\n🎉 Done!")


if __name__ == "__main__":
    main()