"""Paquete `data_structures` — estructuras de datos del proyecto.

Reexporta las clases principales del módulo AVL para permitir:
	from data_structures import ArbolAVL, NodoAVL
"""

from .avl_node import NodoAVL
from .avl_tree import ArbolAVL

__all__ = ["NodoAVL", "ArbolAVL"]

