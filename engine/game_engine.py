"""
GameEngine — núcleo lógico del juego. Sin dependencia de Pygame.

Responsabilidades:
    - Coordinar todos los subsistemas: ConfigLoader, ArbolAVL,
        Carrito, CollisionSystem y CLIRenderer.
    - Ejecutar el game loop lógico (tick a tick).
    - Gestionar el estado del juego: JUGANDO, VICTORIA, DERROTA.
    - Actualizar la cámara para que el carrito siempre sea visible.
    - Construir FrameState cada tick y entregarlo al renderer.
    - Soportar modo interactivo (teclado) y modo automático (headless).

Estrategia de cámara:
    La cámara sigue al carrito con offset fijo CAMARA_OFFSET_X.
    camara_x = carrito.x - (CAMARA_OFFSET_X / pixels_por_metro)
    Así el carrito siempre aparece en el borde izquierdo de la vista,
    coincidiendo con su velocidad de avance (cámara y carrito avanzan
    al mismo ritmo).

Ventana visible:
    x_min = camara_x
    x_max = camara_x + (SCREEN_W / pixels_por_metro)
    El ArbolAVL.rango(x_min, x_max, 0, SCREEN_H) devuelve solo los
    obstáculos que deben dibujarse en ese frame. O(log N + K).

Referencia de algoritmos (TheAlgorithms):
    - Búsqueda por rango AVL: equivalente a Binary Search aplicado en
        árbol BST (ver data_structures/avl_tree.py::rango).
    - Ordenamiento de recorridos: el inorden del AVL produce una lista
        ordenada por (x1, y1), equivalente a un sort estable O(N) ya que
        el árbol mantiene el invariante BST.
"""
from __future__ import annotations

import time
import sys
import select
try:
    import tty
    import termios
except Exception:  # pragma: no cover - platform-specific
    tty = None
    termios = None
from pathlib import Path
from typing import Callable

from core.enums import GameState, Direccion
from core.constants import (
    SCREEN_W, SCREEN_H,
    CAMARA_OFFSET_X,
    PIXELS_POR_METRO,
)
from data_structures.avl_tree import ArbolAVL
from models.carrito import Carrito
from models.game_state import FrameState
from utils.config_loader import ConfigLoader
from engine.collision_system import CollisionSystem
from engine.cli_renderer import CLIRenderer


class GameEngine:
    """
    Motor de juego completo para la simulación CLI.

    Modos de operación:
        run()           — game loop interactivo (con teclado en UNIX).
        run_headless()  — game loop automático sin input (para tests y CI).

    Parámetros de run_headless():
        acciones: lista de tuplas (tick, accion) donde accion es
                    'saltar', 'arriba', 'abajo' o None.
    """

    def __init__(
        self,
        ruta_config: str | Path = "config/game_config.json",
        verbose:     bool       = False,
        velocidad_simulacion: float = 1.0,
    ) -> None:
        self.verbose              = verbose
        self.velocidad_simulacion = velocidad_simulacion

        # Carga de configuración
        self._config = ConfigLoader()
        self._config.cargar(ruta_config)

        self._pixels_por_metro: float = float(
            self._config.get("juego.pixels_por_metro", PIXELS_POR_METRO)
        )
        self._refresh_ms:  int   = int(self._config.get("juego.refresh_ms",  200))
        self._distancia_m: int   = int(self._config.get("juego.distancia_total_m", 1000))
        self._vel_x:       float = float(self._config.get("juego.velocidad_x_ms", 5))
        self._vel_y:       float = float(self._config.get("juego.velocidad_y_ms", 3))
        self._fuerza_salto:float = float(self._config.get("juego.fuerza_salto",   12))
        self._gravedad:    float = float(self._config.get("juego.gravedad",        9.8))
        self._energia_ini: int   = int(self._config.get("juego.energia_inicial",  100))

        # Árbol AVL
        self._arbol = ArbolAVL()
        self._cargar_obstaculos()

        # Carrito
        self._carrito = Carrito(
            x=0.0,
            y=float(SCREEN_H // 2),
            y_suelo=float(SCREEN_H // 2),
            velocidad_x=self._vel_x,
            velocidad_y=self._vel_y,
            fuerza_salto=self._fuerza_salto,
            gravedad=self._gravedad,
            energia=self._energia_ini,
            energia_maxima=self._energia_ini,
            color_base=self._config.color_carrito(),
            color_salto=self._config.color_salto(),
            y_limite_superior=float(SCREEN_H * 0.15),
            y_limite_inferior=float(SCREEN_H * 0.85),
        )

        # Estado del juego
        self._estado:        GameState = GameState.JUGANDO
        self._camara_x:      float     = 0.0
        self._tick:          int       = 0
        self._mostrar_arbol: bool      = False
        self._recorrido_idx: int       = 0
        self._recorridos    = ["bfs", "inorden", "preorden", "postorden"]

        # Renderer CLI
        self._renderer = CLIRenderer(
            ancho=90,
            limpiar_pantalla=not verbose,
            verbose=verbose,
        )

        # Métricas
        self._t_inicio:       float = 0.0
        self._ticks_totales:  int   = 0
        self._colisiones_log: list  = []

    # API pública
    def run(self) -> GameState:
        """
        Game loop interactivo. Lee teclado en modo raw (solo UNIX).
        Retorna el estado final (VICTORIA o DERROTA).
        """
        self._mostrar_bienvenida()

        # Verificar si podemos usar teclado raw
        if sys.platform == "win32" or not sys.stdin.isatty():
            print("  Modo interactivo no disponible en este entorno.")
            print("  Ejecutando en modo automático (headless)...")
            return self.run_headless()

        try:
            return self._loop_interactivo()
        except KeyboardInterrupt:
            print("\n\n  Simulación interrumpida por el usuario.")
            return self._estado

    def run_headless(
        self,
        acciones: list[tuple[int, str | None]] | None = None,
        max_ticks: int | None = None,
    ) -> GameState:
        """
        Game loop automático sin input de teclado.

        Parámetros:
            acciones  : lista de (tick_num, accion). Acciones: 'saltar',
                        'arriba', 'abajo'. Se aplican al tick indicado.
            max_ticks : límite máximo de ticks (por si el juego no termina).

        Retorna el estado final (VICTORIA o DERROTA).
        """
        mapa_acciones: dict[int, str] = {}
        if acciones:
            for tick, accion in acciones:
                if accion:
                    mapa_acciones[tick] = accion

        limite = max_ticks or (self._distancia_m // int(self._vel_x) + 200)
        self._t_inicio = time.time()

        while self._estado == GameState.JUGANDO and self._tick < limite:
            # Aplicar acción programada si existe
            accion = mapa_acciones.get(self._tick)
            if accion:
                self._aplicar_accion(accion)

            self._tick_logico()

            if self.verbose:
                estado_frame = self._construir_frame_state()
                self._renderer.dibujar_tick_log(
                    self._tick,
                    estado_frame,
                    self._colisiones_log,
                )
                self._colisiones_log = []

            # Dormir para respetar refresh_ms en simulación real
            if not self.verbose:
                time.sleep(self._refresh_ms / 1000.0 / self.velocidad_simulacion)

        estado_final = self._construir_frame_state()

        if self.verbose or True:   # siempre mostrar resultado final
            print()
            self._renderer.dibujar_resultado_final(estado_final)
            if self._arbol.total_nodos > 0:
                self._renderer.dibujar_arbol(estado_final)

        return self._estado

    def insertar_obstaculo_manual(
        self,
        x1: int, y1: int, x2: int, y2: int,
        tipo: str, danio: int,
    ) -> bool:
        """
        Inserta un obstáculo en el árbol AVL manualmente (antes o durante el juego).
        Retorna True si fue insertado, False si la clave ya existía.
        """
        from core.enums import TipoObstaculo
        from models.obstaculo import Obstaculo
        try:
            tipo_enum = TipoObstaculo(tipo.upper())
            obs = Obstaculo(x1=x1, y1=y1, x2=x2, y2=y2, tipo=tipo_enum, danio=danio)
            return self._arbol.insertar(obs)
        except (ValueError, Exception) as e:
            print(f"  [GameEngine] Error al insertar obstáculo: {e}")
            return False

    def eliminar_obstaculo(self, x1: int, y1: int) -> bool:
        """Elimina el obstáculo con clave (x1, y1) del árbol AVL."""
        return self._arbol.eliminar(x1, y1)

    def estado_actual(self) -> GameState:
        """Retorna el estado actual del juego."""
        return self._estado

    def arbol(self) -> ArbolAVL:
        """Acceso directo al árbol AVL (para tests e integración)."""
        return self._arbol

    def carrito(self) -> Carrito:
        """Acceso directo al carrito (para tests e integración)."""
        return self._carrito

    # Loop interactivo (UNIX)
    def _loop_interactivo(self) -> GameState:
        """Game loop con captura de teclado en modo raw (UNIX)."""
        fd   = sys.stdin.fileno()
        orig = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            self._t_inicio = time.time()

            while self._estado == GameState.JUGANDO:
                t_tick = time.time()

                # Leer tecla sin bloquear
                if select.select([sys.stdin], [], [], 0)[0]:
                    tecla = sys.stdin.read(1)
                    self._procesar_tecla(tecla)

                self._tick_logico()

                # Renderizar
                if not self.verbose:
                    estado_frame = self._construir_frame_state()
                    if self._mostrar_arbol:
                        self._renderer.dibujar_arbol(estado_frame)
                    else:
                        self._renderer.dibujar_frame(estado_frame)

                # Mantener tempo de refresh_ms
                elapsed_ms = (time.time() - t_tick) * 1000
                sleep_ms   = max(0.0, self._refresh_ms - elapsed_ms)
                time.sleep(sleep_ms / 1000.0)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, orig)

        estado_final = self._construir_frame_state()
        self._renderer.dibujar_resultado_final(estado_final)
        if self._arbol.total_nodos > 0:
            self._renderer.dibujar_arbol(estado_final)

        return self._estado

    # Tick lógico
    def _tick_logico(self) -> None:
        """
        Un paso de la simulación:
            1. Actualizar carrito (posición, física de salto).
            2. Actualizar cámara.
            3. Consultar árbol AVL (rango visible).
            4. Detectar colisiones AABB.
            5. Aplicar daño al carrito.
            6. Verificar condición de fin (victoria/derrota).
        """
        # 1. Actualizar carrito
        self._carrito.actualizar(dt=1.0)
        self._tick += 1
        self._ticks_totales += 1

        # 2. Actualizar cámara
        # El carrito siempre aparece en CAMARA_OFFSET_X píxeles desde el borde izq.
        self._camara_x = self._carrito.x - (CAMARA_OFFSET_X / self._pixels_por_metro)
        self._camara_x = max(0.0, self._camara_x)

        # 3. Consultar rango visible en el AVL
        x_min = self._camara_x
        x_max = x_min + (SCREEN_W / self._pixels_por_metro)
        y_min = 0
        y_max = SCREEN_H

        candidatos = self._arbol.rango(x_min, x_max, y_min, y_max)

        # 4 & 5. Detectar colisiones y aplicar daño
        resultado = CollisionSystem.detectar_con_bbox_mundo(
            self._carrito,
            candidatos,
            camara_x=self._camara_x,
            pixels_por_metro=self._pixels_por_metro,
        )
        if resultado.hubo_colision:
            self._carrito.recibir_danio(resultado.danio_total)
            self._colisiones_log = resultado.obstaculos_hit[:]
            if self.verbose:
                pass  # el log se imprime desde run_headless

        # 6. Verificar fin del juego
        self._verificar_fin()

    def _verificar_fin(self) -> None:
        """Determina si el juego terminó (victoria o derrota)."""
        if not self._carrito.esta_vivo():
            self._estado = GameState.DERROTA
        elif self._carrito.x >= self._distancia_m:
            self._estado = GameState.VICTORIA

    # Input 
    def _procesar_tecla(self, tecla: str) -> None:
        """Mapeo de teclas a acciones del juego."""
        TECLAS = {
            " ":    "saltar",
            "\x1b": "_escape",   # ESC o secuencia de flecha
            "q":    "salir",
            "Q":    "salir",
            "t":    "arbol",
            "T":    "arbol",
            "r":    "recorrido",
            "R":    "recorrido",
        }
        if tecla in TECLAS:
            self._aplicar_accion(TECLAS[tecla])

    def _aplicar_accion(self, accion: str) -> None:
        """Aplica una acción al estado del juego."""
        if accion == "saltar":
            self._carrito.saltar()
        elif accion == "arriba":
            self._carrito.moverse_y(Direccion.ARRIBA)
        elif accion == "abajo":
            self._carrito.moverse_y(Direccion.ABAJO)
        elif accion == "arbol":
            self._mostrar_arbol = not self._mostrar_arbol
        elif accion == "recorrido":
            self._recorrido_idx = (self._recorrido_idx + 1) % len(self._recorridos)
        elif accion == "salir":
            self._estado = GameState.DERROTA

    # Construcción del FrameState 
    def _construir_frame_state(self) -> FrameState:
        """
        Construye el snapshot del estado actual para el renderer.
        Solo contiene lo que el renderer necesita (separación de capas).
        """
        # Obstáculos visibles
        x_min = self._camara_x
        x_max = x_min + (SCREEN_W / self._pixels_por_metro)
        obs_visibles = self._arbol.rango(x_min, x_max, 0, SCREEN_H)

        # Niveles del árbol para la visualización
        niveles = self._arbol.bfs() if self._mostrar_arbol else []

        # Recorrido activo
        recorrido_nombre = self._recorridos[self._recorrido_idx]
        recorrido_lista  = self._obtener_recorrido(recorrido_nombre)

        # FPS lógicos
        elapsed = time.time() - self._t_inicio if self._t_inicio else 1
        fps = self._ticks_totales / elapsed if elapsed > 0 else 0

        return FrameState(
            carrito=self._carrito,
            obstaculos_visibles=obs_visibles,
            estado_juego=self._estado,
            camara_x=self._camara_x,
            distancia_total_m=self._distancia_m,
            pixels_por_metro=self._pixels_por_metro,
            mostrar_arbol=self._mostrar_arbol,
            niveles_arbol=niveles,
            recorrido_actual=recorrido_nombre,
            recorrido_lista=recorrido_lista,
            total_nodos_avl=self._arbol.total_nodos,
            fps_actual=fps,
        )

    def _obtener_recorrido(self, nombre: str):
        """Retorna la lista de obstáculos según el recorrido solicitado."""
        if nombre == "bfs":
            return self._arbol.bfs_lista()
        elif nombre == "inorden":
            return self._arbol.inorden()
        elif nombre == "preorden":
            return self._arbol.preorden()
        elif nombre == "postorden":
            return self._arbol.postorden()
        return []

    # Inicialización 
    def _cargar_obstaculos(self) -> None:
        """Inserta todos los obstáculos del JSON en el árbol AVL."""
        for obs in self._config.obstaculos():
            insertado = self._arbol.insertar(obs)
            if self.verbose and not insertado:
                print(f"  [AVL] Obstáculo duplicado ignorado: {obs.clave_avl()}")

    def _mostrar_bienvenida(self) -> None:
        """Imprime el banner y la configuración al iniciar."""
        resumen = {
            "Distancia total":  f"{self._distancia_m} m",
            "Velocidad carrito":f"{self._vel_x} m/tick",
            "Refresh":          f"{self._refresh_ms} ms",
            "Obstáculos cargados": str(self._arbol.total_nodos),
            "Energía inicial":  f"{self._energia_ini}%",
        }
        self._renderer.imprimir_bienvenida(resumen)