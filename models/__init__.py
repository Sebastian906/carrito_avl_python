"""Paquete `models` — entidades del dominio del juego.

Reexporta las entidades más usadas para facilitar importaciones:
	from models import Carrito, FrameState, Obstaculo
"""

from .carrito import Carrito
from .game_state import FrameState
from .obstaculo import Obstaculo

__all__ = ["Carrito", "FrameState", "Obstaculo"]

