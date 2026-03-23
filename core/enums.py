"""
Enumeraciones globales del proyecto. Sin dependencias externas.
"""
from enum import Enum, auto

class GameState(Enum):
    MENU      = auto()
    JUGANDO   = auto()
    VICTORIA  = auto()
    DERROTA   = auto()
    PAUSA     = auto()
    VER_ARBOL = auto()

class TipoObstaculo(Enum):
    ROCA   = "ROCA"
    BARRIL = "BARRIL"
    CHARCO = "CHARCO"
    MURO   = "MURO"
    CONO   = "CONO"

class Direccion(Enum):
    ARRIBA = auto()
    ABAJO  = auto()