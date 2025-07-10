"""
Redirection vers la nouvelle implémentation modulaire des générateurs
"""

from models.generators import (
    BaseCodeGenerator,
    PythonCodeGenerator,
    JavaScriptCodeGenerator,
    HTMLCodeGenerator,
    CodeGenerator
)

# Garde la classe DocumentGenerator qui n'a pas été migrée
from .document_generator import DocumentGenerator

__all__ = [
    'BaseCodeGenerator',
    'PythonCodeGenerator',
    'JavaScriptCodeGenerator',
    'HTMLCodeGenerator',
    'CodeGenerator',
    'DocumentGenerator'
]