"""
Entidad Obstaculo. Sin dependencia de Pygame.
El método rect() devuelve una tupla simple (x, y, w, h) para no acoplar
este módulo a pygame. El Renderer se encarga de construir el pygame.Rect.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from core.enums import TipoObstaculo
from core.constants import COLORES_OBSTACULOS

@dataclass
class Obstaculo:
    """
    Representa un obstáculo en el mundo del juego.

    Coordenadas en METROS (no píxeles).
    x1, y1: esquina superior-izquierda del área de colisión.
    x2, y2: esquina inferior-derecha del área de colisión.

    Invariante: x1 < x2  y  y1 < y2
    """
    x1: int
    y1: int
    x2: int
    y2: int
    tipo: TipoObstaculo
    danio: int
    eliminado: bool = field(default=False, compare=False)

    # Validación básica
    def __post_init__(self) -> None:
        if self.x1 >= self.x2:
            raise ValueError(
                f"Obstaculo inválido: x1={self.x1} debe ser < x2={self.x2}"
            )
        if self.y1 >= self.y2:
            raise ValueError(
                f"Obstaculo inválido: y1={self.y1} debe ser < y2={self.y2}"
            )
        if self.danio < 0:
            raise ValueError(f"El daño no puede ser negativo: {self.danio}")

    # Clave de inserción en el AVL
    def clave_avl(self) -> tuple[int, int]:
        """Devuelve (x1, y1): clave de comparación en el árbol AVL."""
        return (self.x1, self.y1)

    # Área de colisión (sin Pygame)
    def bbox(self) -> tuple[int, int, int, int]:
        """(x1, y1, x2, y2) — coordenadas mundo en metros."""
        return (self.x1, self.y1, self.x2, self.y2)

    def ancho(self) -> int:
        return self.x2 - self.x1

    def alto(self) -> int:
        return self.y2 - self.y1

    # Color de representación
    def color(self) -> tuple[int, int, int]:
        return COLORES_OBSTACULOS.get(self.tipo.value, (128, 128, 128))

    # Representación legible
    def __repr__(self) -> str:
        estado = "✗" if self.eliminado else "✓"
        return (
            f"Obstaculo({self.tipo.value} "
            f"[{self.x1},{self.y1}]→[{self.x2},{self.y2}] "
            f"dmg={self.danio} {estado})"
        )