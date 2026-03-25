"""Paquete `engine` — núcleo lógico del juego (sin dependencias gráficas).

Reexporta las clases principales para facilitar importaciones:
    from engine import GameEngine, CollisionSystem, CLIRenderer
"""

from .game_engine import GameEngine
from .collision_system import CollisionSystem
from .cli_renderer import CLIRenderer

__all__ = ["GameEngine", "CollisionSystem", "CLIRenderer"]