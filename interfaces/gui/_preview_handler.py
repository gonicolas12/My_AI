"""
Relais : les visionneuses natives vivent dans interfaces/desktop/preview_handler.py

Gardé pour l'interface Tk (artifacts_panel.py) jusqu'à son retrait.
"""

from interfaces.desktop.preview_handler import (  # noqa: F401  # pylint: disable=unused-import
    COMTYPES_AVAILABLE,
    NATIVE_EXTENSIONS,
    AsyncNativePreview,
    NativePreview,
    handler_clsid,
    supports_native_preview,
)
