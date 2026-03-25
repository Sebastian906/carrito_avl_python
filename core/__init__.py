"""Paquete `core` — constantes y enumeraciones compartidas del proyecto.

Este módulo reexporta los símbolos más usados para facilitar
importaciones desde otras capas (por ejemplo: `from core import GameState`).
"""

from .constants import (
	SCREEN_W,
	SCREEN_H,
	FPS,
	TITULO,
	CAMARA_OFFSET_X,
	CARRIL_TOP,
	CARRIL_MID,
	CARRIL_BOT,
	PIXELS_POR_METRO,
	COLOR_CARRITO_DEFAULT,
	COLOR_SALTO_DEFAULT,
	COLORES_OBSTACULOS,
)
from .enums import GameState, TipoObstaculo, Direccion

__all__ = [
	# constantes
	"SCREEN_W",
	"SCREEN_H",
	"FPS",
	"TITULO",
	"CAMARA_OFFSET_X",
	"CARRIL_TOP",
	"CARRIL_MID",
	"CARRIL_BOT",
	"PIXELS_POR_METRO",
	"COLOR_CARRITO_DEFAULT",
	"COLOR_SALTO_DEFAULT",
	"COLORES_OBSTACULOS",
	# enums
	"GameState",
	"TipoObstaculo",
	"Direccion",
]
