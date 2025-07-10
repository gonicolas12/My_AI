#!/usr/bin/env python3
"""
Project Health Check - Comprehensive validation of the AI Assistant project
Checks installation, configuration, dependencies, and functionality.
"""
import sys
import os
import subprocess
import importlib
from pathlib import Path
from typing import List, Tuple, Dict, Any
import json

# Add the project root to the path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))


class HealthChecker:
    """Comprehensive health checker for the AI Assistant project."""
    
    def __init__(self):
        """Initialize the health checker."""
        self.results = []
        self.errors = []
        self.warnings = []
        
    def add_result(self, category: str, test: str, status: str, message: str):
        """Add a test result."""
        self.results.append({
            'category': category,
            'test': test,
            'status': status,
            'message': message
        })
        
        if status == 'ERROR':
            self.errors.append(f"{category}.{test}: {message}")
        elif status == 'WARNING':
            self.warnings.append(f"{category}.{test}: {message}")
    
    def check_python_version(self):
        """Check Python version compatibility."""
        version = sys.version_info
        if version < (3, 8):
            self.add_result('system', 'python_version', 'ERROR', 
                          f"Python {version.major}.{version.minor} < 3.8 (minimum required)")
        elif version < (3, 10):
            self.add_result('system', 'python_version', 'WARNING', 
                          f"Python {version.major}.{version.minor} < 3.10 (recommended)")
        else:
            self.add_result('system', 'python_version', 'OK', 
                          f"Python {version.major}.{version.minor}.{version.micro}")
    
    def check_project_structure(self):
        """Check project directory structure."""
        required_dirs = [
            'core', 'models', 'processors', 'generators', 
            'interfaces', 'utils', 'tests', 'docs', 'examples'
        ]
        
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                self.add_result('structure', f'dir_{dir_name}', 'OK', f"Directory exists: {dir_name}/")
            else:
                self.add_result('structure', f'dir_{dir_name}', 'ERROR', f"Missing directory: {dir_name}/")
        
        # Check essential files
        required_files = [
            'main.py', 'launcher.py', 'requirements.txt', 'config.yaml',
            'README.md', 'QUICKSTART.md', 'demo.py', 'run_tests.py'
        ]
        
        for file_name in required_files:
            file_path = project_root / file_name
            if file_path.exists() and file_path.is_file():
                self.add_result('structure', f'file_{file_name}', 'OK', f"File exists: {file_name}")
            else:
                self.add_result('structure', f'file_{file_name}', 'ERROR', f"Missing file: {file_name}")
    
    def check_dependencies(self):
        """Check if required dependencies are installed."""
        # Critical dependencies
        critical_deps = [
            'click', 'yaml', 'transformers', 'torch', 'rich'
        ]
        
        # Optional dependencies
        optional_deps = [
            'fitz', 'docx', 'tkinter', 'streamlit', 'pytest'
        ]
        
        for dep in critical_deps:
            try:
                importlib.import_module(dep)
                self.add_result('dependencies', f'critical_{dep}', 'OK', f"Critical dependency available: {dep}")
            except ImportError:
                self.add_result('dependencies', f'critical_{dep}', 'ERROR', f"Missing critical dependency: {dep}")
        
        for dep in optional_deps:
            try:
                if dep == 'fitz':
                    import fitz
                elif dep == 'docx':
                    import docx
                elif dep == 'tkinter':
                    import tkinter
                else:
                    importlib.import_module(dep)
                self.add_result('dependencies', f'optional_{dep}', 'OK', f"Optional dependency available: {dep}")
            except ImportError:
                self.add_result('dependencies', f'optional_{dep}', 'WARNING', f"Missing optional dependency: {dep}")
    
    def check_configuration(self):
        """Check configuration files and settings."""
        # Check config.yaml
        config_file = project_root / 'config.yaml'
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check essential config sections
                required_sections = ['llm', 'interface', 'processing', 'logging']
                for section in required_sections:
                    if section in config:
                        self.add_result('config', f'section_{section}', 'OK', f"Config section exists: {section}")
                    else:
                        self.add_result('config', f'section_{section}', 'WARNING', f"Missing config section: {section}")
                
                # Check LLM configuration
                if 'llm' in config:
                    provider = config['llm'].get('provider', 'unknown')
                    self.add_result('config', 'llm_provider', 'OK', f"LLM provider: {provider}")
                
            except Exception as e:
                self.add_result('config', 'config_yaml', 'ERROR', f"Error reading config.yaml: {e}")
        else:
            self.add_result('config', 'config_yaml', 'ERROR', "Missing config.yaml file")
    
    def check_core_modules(self):
        """Check if core modules can be imported and initialized."""
        modules_to_check = [
            ('core.config', 'Config'),
            ('core.ai_engine', 'AIEngine'),
            ('core.conversation', 'ConversationManager'),
            ('models.local_llm', 'LocalLLMManager'),
            ('processors.pdf_processor', 'PDFProcessor'),
            ('processors.docx_processor', 'DOCXProcessor'),
            ('processors.code_processor', 'CodeProcessor'),
            ('generators.code_generator', 'CodeGenerator'),
            ('generators.document_generator', 'DocumentGenerator'),
            ('utils.logger', 'Logger'),
            ('utils.file_manager', 'FileManager'),
            ('utils.validators', 'Validators'),
            ('interfaces.cli', None),  # Module only
        ]
        
        for module_name, class_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                if class_name:
                    getattr(module, class_name)
                    self.add_result('modules', f'class_{class_name}', 'OK', f"Class available: {module_name}.{class_name}")
                else:
                    self.add_result('modules', f'module_{module_name}', 'OK', f"Module available: {module_name}")
            except ImportError as e:
                self.add_result('modules', f'import_{module_name}', 'ERROR', f"Import error: {module_name} - {e}")
            except AttributeError as e:
                self.add_result('modules', f'class_{class_name}', 'ERROR', f"Class not found: {module_name}.{class_name}")
    
    def check_ai_initialization(self):
        """Check if AI engine can be initialized."""
        try:
            from core.config import Config
            from core.ai_engine import AIEngine
            
            config = Config()
            ai_engine = AIEngine(config)
            
            self.add_result('ai', 'engine_creation', 'OK', "AI engine can be created")
            
            # Try to initialize LLM (this might fail if no model is available)
            try:
                success = ai_engine.initialize_llm()
                if success:
                    self.add_result('ai', 'llm_initialization', 'OK', "LLM initialized successfully")
                    
                    # Try a simple response
                    try:
                        response = ai_engine.process_text("Hello")
                        if response and "not initialized" not in response.lower():
                            self.add_result('ai', 'llm_response', 'OK', "LLM can generate responses")
                        else:
                            self.add_result('ai', 'llm_response', 'WARNING', "LLM response indicates issues")
                    except Exception as e:
                        self.add_result('ai', 'llm_response', 'WARNING', f"LLM response error: {e}")
                else:
                    self.add_result('ai', 'llm_initialization', 'WARNING', "LLM initialization failed (expected if no model configured)")
            except Exception as e:
                self.add_result('ai', 'llm_initialization', 'WARNING', f"LLM initialization error: {e}")
                
        except Exception as e:
            self.add_result('ai', 'engine_creation', 'ERROR', f"AI engine creation failed: {e}")
    
    def check_external_tools(self):
        """Check availability of external tools."""
        # Check Ollama
        try:
            result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.add_result('external', 'ollama', 'OK', f"Ollama available: {result.stdout.strip()}")
            else:
                self.add_result('external', 'ollama', 'WARNING', "Ollama not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.add_result('external', 'ollama', 'WARNING', "Ollama not found in PATH")
        
        # Check Git
        try:
            result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.add_result('external', 'git', 'OK', f"Git available: {result.stdout.strip()}")
            else:
                self.add_result('external', 'git', 'WARNING', "Git not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.add_result('external', 'git', 'WARNING', "Git not found in PATH")
    
    def check_interfaces(self):
        """Check if interfaces can be launched."""
        # Check CLI
        try:
            from main import create_cli
            create_cli()
            self.add_result('interfaces', 'cli', 'OK', "CLI interface can be created")
        except Exception as e:
            self.add_result('interfaces', 'cli', 'ERROR', f"CLI interface error: {e}")
        
        # Check GUI
        try:
            import tkinter
            # Try to create a root window
            root = tkinter.Tk()
            root.withdraw()  # Hide it
            root.destroy()
            self.add_result('interfaces', 'gui', 'OK', "GUI interface available (tkinter)")
        except Exception as e:
            self.add_result('interfaces', 'gui', 'WARNING', f"GUI interface not available: {e}")
    
    def check_tests(self):
        """Check if tests can be run."""
        tests_dir = project_root / 'tests'
        if tests_dir.exists():
            test_files = list(tests_dir.glob('test_*.py'))
            if test_files:
                self.add_result('tests', 'test_files', 'OK', f"Found {len(test_files)} test files")
                
                # Try to run a simple test
                try:
                    result = subprocess.run([
                        sys.executable, '-m', 'pytest', '--collect-only', '-q'
                    ], capture_output=True, text=True, timeout=30, cwd=project_root)
                    
                    if result.returncode == 0:
                        self.add_result('tests', 'pytest_collect', 'OK', "Tests can be collected by pytest")
                    else:
                        self.add_result('tests', 'pytest_collect', 'WARNING', f"Pytest collection issues: {result.stderr}")
                except Exception as e:
                    self.add_result('tests', 'pytest_collect', 'WARNING', f"Cannot run pytest: {e}")
            else:
                self.add_result('tests', 'test_files', 'WARNING', "No test files found")
        else:
            self.add_result('tests', 'tests_dir', 'WARNING', "Tests directory missing")
    
    def run_all_checks(self):
        """Run all health checks."""
        print("🔍 Running comprehensive health check...")
        print("=" * 60)
        
        checks = [
            ("System", self.check_python_version),
            ("Project Structure", self.check_project_structure),
            ("Dependencies", self.check_dependencies),
            ("Configuration", self.check_configuration),
            ("Core Modules", self.check_core_modules),
            ("AI Engine", self.check_ai_initialization),
            ("External Tools", self.check_external_tools),
            ("Interfaces", self.check_interfaces),
            ("Tests", self.check_tests),
        ]
        
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}...")
            try:
                check_func()
            except Exception as e:
                self.add_result('system', f'check_{check_name.lower()}', 'ERROR', f"Check failed: {e}")
    
    def print_summary(self):
        """Print health check summary."""
        print("\n" + "=" * 60)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        # Count results by status
        status_counts = {'OK': 0, 'WARNING': 0, 'ERROR': 0}
        for result in self.results:
            status_counts[result['status']] += 1
        
        print(f"✅ OK: {status_counts['OK']}")
        print(f"⚠️  WARNING: {status_counts['WARNING']}")
        print(f"❌ ERROR: {status_counts['ERROR']}")
        
        # Overall health score
        total = sum(status_counts.values())
        if total > 0:
            health_score = (status_counts['OK'] * 2 + status_counts['WARNING']) / (total * 2) * 100
            print(f"\n🏥 Overall Health Score: {health_score:.1f}%")
            
            if health_score >= 90:
                print("🎉 Excellent! Your AI Assistant is ready to go!")
            elif health_score >= 75:
                print("✅ Good! Minor issues that won't affect core functionality.")
            elif health_score >= 50:
                print("⚠️  Fair. Some important features may not work properly.")
            else:
                print("❌ Poor. Significant issues need to be addressed.")
        
        # Print errors and warnings
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors[:5]:  # Show first 5
                print(f"   • {error}")
            if len(self.errors) > 5:
                print(f"   ... and {len(self.errors) - 5} more")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:5]:  # Show first 5
                print(f"   • {warning}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if status_counts['ERROR'] > 0:
            print("   1. Fix critical errors first (marked as ERROR)")
            print("   2. Run: python launcher.py install")
        if status_counts['WARNING'] > 0:
            print("   3. Address warnings for full functionality")
        if 'ollama' in str(self.warnings):
            print("   4. Install Ollama for local AI: https://ollama.ai/")
        if 'tkinter' in str(self.warnings):
            print("   5. Install tkinter for GUI: pip install tk")
        
        print("   6. Run: python launcher.py demo")
        print("   7. Read: QUICKSTART.md for quick setup")
    
    def save_report(self, filename: str = "health_check_report.json"):
        """Save detailed report to JSON file."""
        report = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'project_root': str(project_root),
            'results': self.results,
            'summary': {
                'total_checks': len(self.results),
                'errors': len(self.errors),
                'warnings': len(self.warnings),
                'ok': len([r for r in self.results if r['status'] == 'OK'])
            }
        }
        
        try:
            with open(project_root / filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {filename}")
        except Exception as e:
            print(f"\n⚠️  Could not save report: {e}")


def main():
    """Main health check function."""
    checker = HealthChecker()
    checker.run_all_checks()
    checker.print_summary()
    checker.save_report()
    
    # Exit with error code if critical issues found
    if checker.errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
