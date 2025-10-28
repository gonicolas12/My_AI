"""
VS Code Extension Interface for My AI Personal Assistant.
This module provides integration with VS Code as an extension.

Note: This is a Python implementation for the backend.
The actual VS Code extension would be written in TypeScript/JavaScript.
"""

import json
import sys
import os
import argparse
from typing import Dict, Any, Optional
from core.ai_engine import AIEngine
from core.config import Config
from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor
from processors.code_processor import CodeProcessor
from models.advanced_code_generator import AdvancedCodeGenerator as CodeGenerator
from utils.logger import Logger
from utils.file_manager import FileManager

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VSCodeExtensionBackend:
    """Backend service for VS Code extension integration."""

    def __init__(self):
        """Initialize the VS Code extension backend."""
        self.logger = Logger.get_logger("vscode_extension")
        self.config = Config()
        self.ai_engine = AIEngine(self.config)
        self.file_manager = FileManager()

        # Processors and generators
        self.pdf_processor = PDFProcessor()
        self.docx_processor = DOCXProcessor()
        self.code_processor = CodeProcessor()
        self.code_generator = CodeGenerator()

        # Initialize AI
        self.ai_initialized = False
        self.initialize_ai()

    def initialize_ai(self) -> bool:
        """Initialize the AI engine."""
        try:
            self.ai_initialized = self.ai_engine.initialize_llm()
            if self.ai_initialized:
                self.logger.info("AI engine initialized successfully")
            else:
                self.logger.warning("Failed to initialize AI engine")
            return self.ai_initialized
        except Exception as e:
            self.logger.error("Error initializing AI: %s", e)
            return False

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests from VS Code extension."""
        try:
            command = request.get("command")
            params = request.get("params", {})

            if command == "chat":
                return self.handle_chat(params)
            elif command == "process_file":
                return self.handle_process_file(params)
            elif command == "generate_code":
                return self.handle_generate_code(params)
            elif command == "analyze_code":
                return self.handle_analyze_code(params)
            elif command == "get_status":
                return self.handle_get_status()
            else:
                return {"success": False, "error": f"Unknown command: {command}"}

        except Exception as e:
            self.logger.error("Error handling request: %s", e)
            return {"success": False, "error": str(e)}

    def handle_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat/conversation requests."""
        message = params.get("message", "")

        if not message:
            return {"success": False, "error": "No message provided"}

        if not self.ai_initialized:
            return {"success": False, "error": "AI engine not initialized"}

        try:
            response = self.ai_engine.process_text(message)
            return {
                "success": True,
                "response": response,
                "conversation_history": self.ai_engine.get_conversation_history(),
            }
        except Exception as e:
            return {"success": False, "error": f"Error processing message: {e}"}

    def handle_process_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file processing requests."""
        file_path = params.get("file_path", "")
        file_type = params.get("file_type", "auto")

        if not file_path or not os.path.exists(file_path):
            return {"success": False, "error": "Invalid file path"}

        try:
            # Auto-detect file type if not specified
            if file_type == "auto":
                extension = self.file_manager.get_file_extension(file_path).lower()
                if extension == ".pdf":
                    file_type = "pdf"
                elif extension == ".docx":
                    file_type = "docx"
                elif extension in [".py", ".js", ".html", ".css", ".cpp", ".java"]:
                    file_type = "code"
                else:
                    file_type = "text"

            # Process based on file type
            if file_type == "pdf":
                text = self.pdf_processor.extract_text(file_path)
                if text:
                    return {
                        "success": True,
                        "file_type": "pdf",
                        "content": text,
                        "length": len(text),
                        "summary": (
                            self._generate_summary(text)
                            if self.ai_initialized
                            else None
                        ),
                    }

            elif file_type == "docx":
                text = self.docx_processor.extract_text(file_path)
                if text:
                    return {
                        "success": True,
                        "file_type": "docx",
                        "content": text,
                        "length": len(text),
                        "summary": (
                            self._generate_summary(text)
                            if self.ai_initialized
                            else None
                        ),
                    }

            elif file_type == "code":
                code = self.code_processor.read_code_file(file_path)
                if code:
                    language = self.code_processor.detect_language(file_path)
                    is_valid = self.code_processor.validate_syntax(code)

                    return {
                        "success": True,
                        "file_type": "code",
                        "content": code,
                        "language": language,
                        "is_valid": is_valid,
                        "lines": len(code.split("\n")),
                        "analysis": (
                            self._analyze_code(code, language)
                            if self.ai_initialized
                            else None
                        ),
                    }

            else:
                # Generic text file
                content = self.file_manager.read_file(file_path)
                if content:
                    return {
                        "success": True,
                        "file_type": "text",
                        "content": content,
                        "length": len(content),
                    }

            return {"success": False, "error": "Failed to process file"}

        except Exception as e:
            return {"success": False, "error": f"Error processing file: {e}"}

    def handle_generate_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation requests."""
        if not self.ai_initialized:
            return {"success": False, "error": "AI engine not initialized"}

        try:
            code_type = params.get("type", "function")  # function, class, module
            language = params.get("language", "python")
            description = params.get("description", "")
            specifications = params.get("specifications", {})

            if code_type == "function":
                code = self.code_generator.generate_function(
                    description,
                    language,
                    specifications.get("parameters", []),
                    specifications.get("return_type", "Any"),
                )
            elif code_type == "class":
                code = self.code_generator.generate_class(
                    description,
                    language,
                    specifications.get("class_name", "GeneratedClass"),
                )
            else:
                # Use AI directly for other types
                prompt = f"Generate {language} {code_type} code: {description}"
                code = self.ai_engine.process_text(prompt)

            if code:
                # Validate generated code
                is_valid = self.code_processor.validate_syntax(code)

                return {
                    "success": True,
                    "code": code,
                    "language": language,
                    "type": code_type,
                    "is_valid": is_valid,
                }
            else:
                return {"success": False, "error": "Failed to generate code"}

        except Exception as e:
            return {"success": False, "error": f"Error generating code: {e}"}

    def handle_analyze_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code analysis requests."""
        if not self.ai_initialized:
            return {"success": False, "error": "AI engine not initialized"}

        try:
            code = params.get("code", "")
            language = params.get("language", "python")
            analysis_type = params.get(
                "analysis_type", "general"
            )  # general, security, performance, style

            if not code:
                return {"success": False, "error": "No code provided"}

            # Basic validation
            is_valid = self.code_processor.validate_syntax(code)

            # AI analysis
            if analysis_type == "security":
                prompt = f"Analyze this {language} code for security vulnerabilities:\n\n{code}"
            elif analysis_type == "performance":
                prompt = f"Analyze this {language} code for performance issues and optimizations:\n\n{code}"
            elif analysis_type == "style":
                prompt = f"Analyze this {language} code for style and best practices:\n\n{code}"
            else:
                prompt = f"Provide a comprehensive analysis of this {language} code:\n\n{code}"

            analysis = self.ai_engine.process_text(prompt)

            return {
                "success": True,
                "is_valid": is_valid,
                "analysis": analysis,
                "language": language,
                "analysis_type": analysis_type,
            }

        except Exception as e:
            return {"success": False, "error": f"Error analyzing code: {e}"}

    def handle_get_status(self) -> Dict[str, Any]:
        """Handle status requests."""
        return {
            "success": True,
            "status": {
                "ai_initialized": self.ai_initialized,
                "ai_model": self.config.get("llm.provider", "unknown"),
                "version": "1.0.0",
                "capabilities": {
                    "chat": True,
                    "file_processing": True,
                    "code_generation": self.ai_initialized,
                    "code_analysis": self.ai_initialized,
                },
            },
        }

    def _generate_summary(self, text: str) -> Optional[str]:
        """Generate a summary of text content."""
        try:
            if len(text) > 2000:
                text = text[:2000] + "..."

            prompt = f"Please provide a brief summary of this content:\n\n{text}"
            return self.ai_engine.process_text(prompt)
        except Exception as e:
            self.logger.error("Error generating summary: %s", e)
            return None

    def _analyze_code(self, code: str, language: str) -> Optional[str]:
        """Analyze code content."""
        try:
            if len(code) > 1500:
                code = code[:1500] + "..."

            prompt = f"Analyze this {language} code and provide insights:\n\n{code}"
            return self.ai_engine.process_text(prompt)
        except Exception as e:
            self.logger.error("Error analyzing code: %s", e)
            return None


class VSCodeCommunicator:
    """Handles communication with VS Code extension."""

    def __init__(self):
        """Initialize the communicator."""
        self.backend = VSCodeExtensionBackend()
        self.logger = Logger.get_logger("vscode_communicator")

    def start_server(self, port: int = 8765):
        """Start the communication server."""
        try:
            # This would typically be a WebSocket or HTTP server
            # For now, we'll implement a simple stdin/stdout communication
            self.logger.info("Starting VS Code communication server on port %s", port)
            self.listen_stdin()
        except Exception as e:
            self.logger.error("Error starting server: %s", e)

    def listen_stdin(self):
        """Listen for requests on stdin (for simple communication)."""
        self.logger.info("Listening for requests on stdin...")

        try:
            while True:
                line = input()
                if line.strip() == "exit":
                    break

                try:
                    request = json.loads(line)
                    response = self.backend.handle_request(request)
                    print(json.dumps(response))
                except json.JSONDecodeError:
                    error_response = {"success": False, "error": "Invalid JSON request"}
                    print(json.dumps(error_response))
                except Exception as e:
                    error_response = {"success": False, "error": str(e)}
                    print(json.dumps(error_response))

        except KeyboardInterrupt:
            self.logger.info("Communication server stopped")
        except EOFError:
            self.logger.info("Input stream closed")


def create_vscode_extension_template():
    """Create a template for the actual VS Code extension."""
    extension_template = """
# VS Code Extension Template

This directory contains the template for creating a VS Code extension that integrates with the AI Assistant.

## Files to create:

1. **package.json** - Extension manifest
2. **src/extension.ts** - Main extension code
3. **src/aiAssistantProvider.ts** - AI Assistant integration
4. **webview/index.html** - Chat interface
5. **webview/script.js** - Frontend logic

## Key features to implement:

- Command palette integration
- Sidebar panel for chat
- File processing commands
- Code generation commands
- Status bar integration
- Settings/configuration

## Commands to register:

- `aiassistant.chat` - Open chat panel
- `aiassistant.processFile` - Process current file
- `aiassistant.generateFunction` - Generate function
- `aiassistant.generateClass` - Generate class
- `aiassistant.analyzeCode` - Analyze selected code

## Communication:

The extension should communicate with this Python backend via:
- Child process spawning
- JSON message passing
- Standard input/output streams

## Installation:

1. Create the extension using `yo code`
2. Implement the TypeScript files
3. Package with `vsce package`
4. Install the .vsix file
"""

    return extension_template


def main():
    """Main entry point for VS Code extension backend."""

    parser = argparse.ArgumentParser(description="VS Code Extension Backend")
    parser.add_argument(
        "--mode",
        choices=["server", "stdin"],
        default="stdin",
        help="Communication mode",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Server port (for server mode)"
    )

    args = parser.parse_args()

    communicator = VSCodeCommunicator()

    if args.mode == "server":
        communicator.start_server(args.port)
    else:
        communicator.listen_stdin()


if __name__ == "__main__":
    main()
