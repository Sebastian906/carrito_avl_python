"""
Snapshot inmutable del estado del juego que se pasa al Renderer cada frame.

Por qué existe esta clase:
    El Renderer no debe acceder directamente a GameEngine ni a ArbolAVL.
    GameEngine construye un GameState cada frame con solo lo que Renderer necesita,
    respetando la separación de capas del patrón MVC (GameEngine = Controller,
    GameState = datos del frame, Renderer = View).

Campos:
    - carrito           : referencia al Carrito actual.
    - obstaculos_visibles: lista de Obstaculo dentro del viewport (del AVL.rango()).
    - camara_x          : posición de la cámara en metros (para transformación mundo->pantalla).
    - distancia_total_m : longitud total de la carretera.
    - pixels_por_metro  : escala de conversión.
    - estado_juego      : GameState enum (JUGANDO, VICTORIA, DERROTA...).
    - mostrar_arbol     : True si el jugador pidió ver el árbol AVL (tecla T).
    - niveles_arbol     : resultado de ArbolAVL.bfs() para AVLVisualizer.
    - recorrido_actual  : nombre del recorrido seleccionado para mostrar ('inorden', etc.).
    - recorrido_lista   : lista plana de obstáculos del recorrido seleccionado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.enums import GameState
from models.obstaculo import Obstaculo

if TYPE_CHECKING:
    from models.carrito import Carrito
    from data_structures.avl_node import NodoAVL

@dataclass
class FrameState:
    """
    Snapshot del estado del juego para un frame concreto.
    GameEngine lo construye y lo entrega a Renderer.dibujar_escena().
    """

    # Estado central 
    carrito:             "Carrito"
    obstaculos_visibles: list[Obstaculo]
    estado_juego:        GameState

    # Cámara y escala 
    camara_x:          float
    distancia_total_m: int
    pixels_por_metro:  float = 10.0

    # Visualización del árbol AVL (tecla T) 
    mostrar_arbol:    bool                    = False
    niveles_arbol:    list[list["NodoAVL"]]   = field(default_factory=list)
    recorrido_actual: str                     = "bfs"      # 'inorden'|'preorden'|'postorden'|'bfs'
    recorrido_lista:  list[Obstaculo]         = field(default_factory=list)

    # Métricas de debug (opcionales)
    total_nodos_avl:  int = 0
    fps_actual:       float = 0.0

    # Helpers de consulta
    def distancia_recorrida_m(self) -> float:
        """Metros recorridos por el carrito desde el inicio."""
        return self.carrito.x

    def porcentaje_progreso(self) -> float:
        """Progreso [0.0 .. 1.0] hacia la meta."""
        if self.distancia_total_m <= 0:
            return 0.0
        return min(1.0, self.carrito.x / self.distancia_total_m)

    def esta_en_meta(self) -> bool:
        return self.carrito.x >= self.distancia_total_m

    def __repr__(self) -> str:
        return (
            f"FrameState("
            f"x={self.carrito.x:.1f}m/{self.distancia_total_m}m, "
            f"energia={self.carrito.energia}, "
            f"obs_visibles={len(self.obstaculos_visibles)}, "
            f"estado={self.estado_juego.name})"
        )