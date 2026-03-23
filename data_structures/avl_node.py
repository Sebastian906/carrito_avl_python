"""
Nodo del árbol AVL. Sin dependencia de Pygame ni de ninguna capa superior.
"""
from __future__ import annotations
from models.obstaculo import Obstaculo

class NodoAVL:
    """
    Nodo de un árbol AVL.

    Clave de comparación: (obstaculo.x1, obstaculo.y1)
    Orden: primero por x1; en caso de empate, por y1.
    """

    __slots__ = ("obstaculo", "izquierdo", "derecho", "altura")

    def __init__(self, obstaculo: Obstaculo) -> None:
        self.obstaculo: Obstaculo         = obstaculo
        self.izquierdo: NodoAVL | None    = None
        self.derecho:   NodoAVL | None    = None
        self.altura:    int               = 1          # hoja recién creada

    # Clave
    def clave(self) -> tuple[int, int]:
        """Devuelve (x1, y1) del obstáculo almacenado."""
        return self.obstaculo.clave_avl()

    # Factor de balance
    @property
    def factor_balance(self) -> int:
        """altura(izq) - altura(der).  ∈ {-1, 0, 1} en árbol balanceado."""
        h_izq = self.izquierdo.altura if self.izquierdo else 0
        h_der = self.derecho.altura   if self.derecho   else 0
        return h_izq - h_der

    # Actualización de altura
    def actualizar_altura(self) -> None:
        h_izq = self.izquierdo.altura if self.izquierdo else 0
        h_der = self.derecho.altura   if self.derecho   else 0
        self.altura = 1 + max(h_izq, h_der)

    # Representación
    def __repr__(self) -> str:
        return f"NodoAVL(clave={self.clave()}, h={self.altura}, fb={self.factor_balance})"