"""
My_AI Relay - Accès mobile à votre IA locale.

Permet de discuter avec My_AI depuis un téléphone via une interface web
mobile-friendly, avec synchronisation en temps réel sur le GUI desktop.
"""

from .relay_bridge import RelayBridge
from .relay_server import RelayServer

__all__ = ["RelayBridge", "RelayServer"]
