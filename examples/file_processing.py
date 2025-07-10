"""
Example: File Processing with My AI Assistant
Demonstrates how to process PDF and DOCX files.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_engine import AIEngine
from core.config import Config
from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor
from utils.logger import Logger


def main():
    """Demonstrate file processing capabilities."""
    # Setup logging
    logger = Logger.get_logger("file_processing_example")
    
    print("🤖 My AI Assistant - File Processing Example")
    print("=" * 50)
    
    # Initialize configuration and AI engine
    config = Config()
    ai_engine = AIEngine(config)
    
    # Initialize processors
    pdf_processor = PDFProcessor()
    docx_processor = DOCXProcessor()
    
    # Example file paths (you can modify these)
    example_files = {
        'pdf': 'example.pdf',
        'docx': 'example.docx'
    }
    
    print("\n📁 File Processing Demonstration:")
    
    # Process PDF file
    print(f"\n1. Processing PDF file: {example_files['pdf']}")
    if os.path.exists(example_files['pdf']):
        if pdf_processor.validate_pdf(example_files['pdf']):
            text = pdf_processor.extract_text(example_files['pdf'])
            if text:
                print(f"   ✅ Successfully extracted {len(text)} characters")
                print(f"   📄 Preview: {text[:200]}...")
                
                # Use AI to summarize the content
                if ai_engine.initialize_llm():
                    summary_prompt = f"Please provide a brief summary of this text:\n\n{text[:1000]}"
                    summary = ai_engine.process_text(summary_prompt)
                    print(f"   🤖 AI Summary: {summary}")
                else:
                    print("   ⚠️  LLM not available for summarization")
            else:
                print("   ❌ Failed to extract text")
        else:
            print("   ❌ Invalid PDF file")
    else:
        print("   ⚠️  File not found - create an example.pdf to test")
    
    # Process DOCX file
    print(f"\n2. Processing DOCX file: {example_files['docx']}")
    if os.path.exists(example_files['docx']):
        if docx_processor.validate_docx(example_files['docx']):
            text = docx_processor.extract_text(example_files['docx'])
            if text:
                print(f"   ✅ Successfully extracted {len(text)} characters")
                print(f"   📄 Preview: {text[:200]}...")
                
                # Use AI to analyze the document structure
                if ai_engine.llm_manager:
                    analysis_prompt = f"Analyze the structure and content of this document:\n\n{text[:1000]}"
                    analysis = ai_engine.process_text(analysis_prompt)
                    print(f"   🤖 AI Analysis: {analysis}")
            else:
                print("   ❌ Failed to extract text")
        else:
            print("   ❌ Invalid DOCX file")
    else:
        print("   ⚠️  File not found - create an example.docx to test")
    
    # Batch processing example
    print(f"\n3. Batch Processing Example:")
    file_extensions = ['.pdf', '.docx', '.txt']
    current_dir = os.getcwd()
    
    for ext in file_extensions:
        files = [f for f in os.listdir(current_dir) if f.endswith(ext)]
        print(f"   📁 Found {len(files)} {ext} files")
        
        for file in files[:3]:  # Process first 3 files of each type
            print(f"      - {file}")
            if ext == '.pdf':
                text = pdf_processor.extract_text(file)
            elif ext == '.docx':
                text = docx_processor.extract_text(file)
            else:
                # Handle text files
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception:
                    text = None
            
            if text:
                print(f"        ✅ Extracted {len(text)} characters")
            else:
                print(f"        ❌ Failed to extract text")
    
    print("\n🎉 File processing demonstration completed!")
    print("\nTips:")
    print("- Place PDF and DOCX files in the project directory to test")
    print("- Ensure LLM is properly configured for AI-powered analysis")
    print("- Check the logs for detailed processing information")


if __name__ == "__main__":
    main()
