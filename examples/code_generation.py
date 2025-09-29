"""
Example: Code Generation with My AI Assistant
Demonstrates how to generate and validate code using AI.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_engine import AIEngine
from core.config import Config
from models.advanced_code_generator import AdvancedCodeGenerator as CodeGenerator
from processors.code_processor import CodeProcessor
from utils.logger import Logger
from utils.file_manager import FileManager


def main():
    """Demonstrate code generation capabilities."""
    # Setup logging
    logger = Logger.get_logger("code_generation_example")
    
    print("🤖 My AI Assistant - Code Generation Example")
    print("=" * 50)
    
    # Initialize components
    config = Config()
    ai_engine = AIEngine(config)
    code_generator = CodeGenerator()
    code_processor = CodeProcessor()
    file_manager = FileManager()
    
    # Initialize LLM
    if not ai_engine.initialize_llm():
        print("⚠️  LLM not available. Some features will be limited.")
    
    print("\n🔧 Code Generation Demonstration:")
    
    # Example 1: Generate a Python function
    print("\n1. Generating a Python function:")
    function_request = {
        'language': 'python',
        'type': 'function',
        'description': 'A function to calculate the factorial of a number',
        'parameters': ['n: int'],
        'return_type': 'int'
    }
    
    python_code = code_generator.generate_function(
        function_request['description'],
        function_request['language'],
        function_request['parameters'],
        function_request['return_type']
    )
    
    if python_code:
        print("   ✅ Generated Python function:")
        print("   " + "─" * 40)
        for line in python_code.split('\n'):
            print(f"   {line}")
        print("   " + "─" * 40)
        
        # Validate the generated code
        is_valid = code_processor.validate_syntax(python_code, 'python')
        print(f"   🔍 Syntax validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        # Save to file
        output_file = "generated_factorial.py"
        if file_manager.write_file(output_file, python_code):
            print(f"   💾 Saved to: {output_file}")
    else:
        print("   ❌ Failed to generate Python function")
    
    # Example 2: Generate an HTML page
    print("\n2. Generating an HTML page:")
    html_request = {
        'language': 'html',
        'type': 'webpage',
        'description': 'A simple contact form with name, email, and message fields'
    }
    
    html_code = code_generator.generate_html_page(
        html_request['description'],
        "Contact Form"
    )
    
    if html_code:
        print("   ✅ Generated HTML page:")
        print("   " + "─" * 40)
        # Show first few lines
        lines = html_code.split('\n')
        for line in lines[:10]:
            print(f"   {line}")
        if len(lines) > 10:
            print("   ...")
        print("   " + "─" * 40)
        
        # Save to file
        output_file = "generated_contact_form.html"
        if file_manager.write_file(output_file, html_code):
            print(f"   💾 Saved to: {output_file}")
    else:
        print("   ❌ Failed to generate HTML page")
    
    # Example 3: Generate a Python class
    print("\n3. Generating a Python class:")
    class_request = {
        'language': 'python',
        'type': 'class',
        'description': 'A Person class with name, age, and email attributes, including validation methods'
    }
    
    class_code = code_generator.generate_class(
        class_request['description'],
        class_request['language'],
        "Person"
    )
    
    if class_code:
        print("   ✅ Generated Python class:")
        print("   " + "─" * 40)
        for line in class_code.split('\n'):
            print(f"   {line}")
        print("   " + "─" * 40)
        
        # Validate and save
        is_valid = code_processor.validate_syntax(class_code, 'python')
        print(f"   🔍 Syntax validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        output_file = "generated_person_class.py"
        if file_manager.write_file(output_file, class_code):
            print(f"   💾 Saved to: {output_file}")
    else:
        print("   ❌ Failed to generate Python class")
    
    # Example 4: Generate API documentation
    print("\n4. Generating API documentation:")
    api_code = '''
def get_user(user_id: int) -> dict:
    """Get user information by ID."""
    pass

def create_user(name: str, email: str) -> dict:
    """Create a new user."""
    pass

def update_user(user_id: int, data: dict) -> dict:
    """Update user information."""
    pass
'''
    
    documentation = code_generator.generate_documentation(api_code, 'python')
    
    if documentation:
        print("   ✅ Generated API documentation:")
        print("   " + "─" * 40)
        for line in documentation.split('\n')[:15]:
            print(f"   {line}")
        print("   " + "─" * 40)
        
        output_file = "generated_api_docs.md"
        if file_manager.write_file(output_file, documentation):
            print(f"   💾 Saved to: {output_file}")
    else:
        print("   ❌ Failed to generate documentation")
    
    # Example 5: Code analysis and suggestions
    print("\n5. Code analysis and suggestions:")
    sample_code = '''
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total
'''
    
    if ai_engine.llm_manager:
        analysis_prompt = f"""
Analyze this Python code and provide suggestions for improvement:

{sample_code}

Please provide:
1. Code quality assessment
2. Performance improvements
3. Best practices recommendations
4. Refactored version if needed
"""
        
        analysis = ai_engine.process_text(analysis_prompt)
        print("   🤖 AI Code Analysis:")
        print("   " + "─" * 40)
        for line in analysis.split('\n')[:10]:
            print(f"   {line}")
        print("   " + "─" * 40)
    else:
        print("   ⚠️  LLM not available for code analysis")
    
    print("\n🎉 Code generation demonstration completed!")
    print("\nGenerated files:")
    print("- generated_factorial.py")
    print("- generated_contact_form.html")
    print("- generated_person_class.py")
    print("- generated_api_docs.md")
    print("\nTips:")
    print("- Configure your LLM properly for better code generation")
    print("- Always validate generated code before using in production")
    print("- Use the code processor for syntax checking and analysis")


if __name__ == "__main__":
    main()
