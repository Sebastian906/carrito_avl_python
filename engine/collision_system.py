"""
Sistema de detección de colisiones AABB (Axis-Aligned Bounding Box).

Responsabilidades:
    - Detectar colisiones entre el carrito y obstáculos visibles.
    - Retornar la lista de obstáculos con los que hubo colisión.
    - Marcar obstáculos como eliminados tras la colisión para que
      no vuelvan a procesarse (evitar daño repetido por tick).

Sin dependencia de Pygame ni de ninguna capa gráfica.

Algoritmo AABB estándar:
    Dos rectángulos A y B NO colisionan si:
        A está completamente a la izquierda de B  (A.x2 <= B.x1)
        A está completamente a la derecha de B    (A.x1 >= B.x2)
        A está completamente arriba de B          (A.y2 <= B.y1)
        A está completamente abajo de B           (A.y1 >= B.y2)
    En cualquier otro caso: hay colisión.

Referencia TheAlgorithms / binary_search aplicado a búsqueda por rango
en el árbol AVL (ver avl_tree.py::rango), que ya implementa la consulta
O(log N + K). CollisionSystem solo procesa la lista K de candidatos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.carrito import Carrito
    from models.obstaculo import Obstaculo


@dataclass
class ColisionResult:
    """
    Resultado de una pasada de detección de colisiones.

    Atributos:
        hubo_colision   : True si al menos un obstáculo fue impactado.
        obstaculos_hit  : lista de obstáculos con los que colisionó.
        danio_total     : suma de daño aplicado en este tick.
    """
    hubo_colision:  bool = False
    obstaculos_hit: list["Obstaculo"] = field(default_factory=list)
    danio_total:    int = 0

    def __repr__(self) -> str:
        if not self.hubo_colision:
            return "ColisionResult(sin colisión)"
        tipos = [o.tipo.value for o in self.obstaculos_hit]
        return f"ColisionResult(hit={tipos}, daño={self.danio_total})"


class CollisionSystem:
    """
    Detecta colisiones AABB entre el carrito y una lista de obstáculos.

    Uso típico (dentro del game loop):
        candidatos = arbol.rango(camara_x, camara_x + vista_w, y_min, y_max)
        resultado  = CollisionSystem.detectar(carrito, candidatos, camara_x, escala)
        if resultado.hubo_colision:
            carrito.recibir_danio(resultado.danio_total)
    """

    @staticmethod
    def detectar(
        carrito:          "Carrito",
        candidatos:       list["Obstaculo"],
        camara_x:         float = 0.0,
        pixels_por_metro: float = 10.0,
    ) -> ColisionResult:
        """
        Recorre la lista de candidatos y aplica AABB contra el carrito.

        Parámetros:
            carrito          : entidad principal del juego.
            candidatos       : obstáculos devueltos por ArbolAVL.rango().
            camara_x         : desplazamiento de cámara en metros.
            pixels_por_metro : escala mundo->pantalla.

        Retorna ColisionResult con todos los impactos del tick.

        Complejidad: O(K) donde K = len(candidatos).
        La selección de candidatos O(log N + K) ya fue hecha por el AVL.
        """
        resultado = ColisionResult()

        for obs in candidatos:
            if obs.eliminado:
                continue

            # Convertir coordenadas del obstáculo (metros) a píxeles de pantalla
            obs_x1_px = (obs.x1 - camara_x) * pixels_por_metro
            obs_x2_px = (obs.x2 - camara_x) * pixels_por_metro
            obs_y1_px = float(obs.y1)
            obs_y2_px = float(obs.y2)

            if carrito.colisiona_con(
                obs_x1_px, obs_y1_px,
                obs_x2_px, obs_y2_px,
                camara_x=0.0,           # bbox() ya recibe camara_x directamente
                pixels_por_metro=1.0,   # ya convertido arriba
            ):
                # Marcar obstáculo para no repetir daño en ticks sucesivos
                obs.eliminado = True
                resultado.hubo_colision  = True
                resultado.danio_total   += obs.danio
                resultado.obstaculos_hit.append(obs)

        return resultado

    @staticmethod
    def detectar_con_bbox_mundo(
        carrito:          "Carrito",
        candidatos:       list["Obstaculo"],
        camara_x:         float = 0.0,
        pixels_por_metro: float = 10.0,
    ) -> ColisionResult:
        """
        Variante que trabaja completamente en coordenadas PANTALLA.
        Útil para el CLI donde no hay transformación visual.

        El carrito convierte su posición x (metros) a píxeles usando
        camara_x y pixels_por_metro. Los obstáculos hacen lo mismo.
        """
        resultado = ColisionResult()

        # Bounding box del carrito en píxeles de pantalla
        cx1, cy1, cx2, cy2 = carrito.bbox(camara_x, pixels_por_metro)

        for obs in candidatos:
            if obs.eliminado:
                continue

            # Obstáculo: x en metros -> píxeles de pantalla; y ya en píxeles
            ox1 = (obs.x1 - camara_x) * pixels_por_metro
            oy1 = float(obs.y1)
            ox2 = (obs.x2 - camara_x) * pixels_por_metro
            oy2 = float(obs.y2)

            # AABB: hay colisión si los rectángulos se superponen
            sin_colision = (cx2 <= ox1) or (cx1 >= ox2) or (cy2 <= oy1) or (cy1 >= oy2)

            if not sin_colision:
                obs.eliminado = True
                resultado.hubo_colision  = True
                resultado.danio_total   += obs.danio
                resultado.obstaculos_hit.append(obs)

        return resultado