"""
Entidad Carrito. Sin dependencia de Pygame.

El carrito vive en coordenadas MUNDO (metros en X, píxeles en Y).
El Renderer es quien convierte a coordenadas de pantalla.

Responsabilidades (según UML y diagrama de flujo):
    - Avance automático en X cada tick.
    - Control en Y mediante moverse_y(direccion).
    - Física del salto: impulso inicial + gravedad hasta aterrizar.
    - Sistema de energía: recibir_danio(), esta_vivo().
    - Cambio de color al saltar y al aterrizar.
    - bbox() para detección de colisiones AABB (sin Pygame).

Física del salto:
    Al presionar ESPACIO:
        velocidad_salto_actual = -fuerza_salto   (hacia arriba, Y decrece)
    Cada tick:
        y += velocidad_salto_actual * dt
        velocidad_salto_actual += gravedad * dt
    Cuando y >= y_suelo: aterrizar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from core.enums import Direccion

@dataclass
class Carrito:
    """
    Entidad principal del juego.

    Coordenadas:
        x  : posición en el mundo (metros). Avanza automáticamente.
        y  : altura en píxeles dentro de la pantalla.
        y_suelo: Y de referencia del carril en que está parado.

    El carrito ocupa un rectángulo de ancho x alto píxeles centrado en (x_pantalla, y).
    """

    # Posición y movimiento
    x:             float                    # posición en metros (eje mundo)
    y:             float                    # posición en píxeles (eje pantalla)
    y_suelo:       float                    # Y del suelo actual (píxeles)
    velocidad_x:   float                    # metros por tick (avance automático)
    velocidad_y:   float                    # píxeles por tick (control en Y)

    # Dimensiones del carrito (píxeles)
    ancho: int = 40
    alto:  int = 30

    # Energía
    energia:         int  = 100
    energia_maxima:  int  = 100

    # Salto
    saltando:               bool  = False
    fuerza_salto:           float = 12.0    # velocidad inicial (píxeles/tick, hacia arriba)
    gravedad:               float = 9.8     # aceleración gravitacional (píxeles/tick²)
    _vel_salto_actual:      float = field(default=0.0, init=False, repr=False)

    # Colores (tuplas RGB)
    color_base:    tuple[int, int, int] = (58, 123, 213)
    color_salto:   tuple[int, int, int] = (245, 166, 35)
    color_actual:  tuple[int, int, int] = field(init=False)

    # Límites de movimiento en Y (píxeles)
    y_limite_superior: float = 100.0
    y_limite_inferior: float = 600.0

    def __post_init__(self) -> None:
        # color_actual arranca igual que color_base
        # (no se puede poner en el field default porque depende de color_base)
        self.color_actual = self.color_base

    # Actualización por Tick
    def actualizar(self, dt: float = 1.0) -> None:
        """
        Aplica un tick de simulación.
            1. Avance automático en X.
            2. Física del salto (si está saltando).
        dt = 1.0 corresponde a un tick lógico completo (refresh_ms).
        """
        # 1. Avance automático en X (siempre)
        self.x += self.velocidad_x * dt

        # 2. Física del salto
        if self.saltando:
            self.y                 += self._vel_salto_actual * dt
            self._vel_salto_actual += self.gravedad * dt      # gravedad jala hacia abajo

            # Detectar aterrizaje
            if self.y >= self.y_suelo:
                self._aterrizar()

    # Control de movimiento
    def saltar(self) -> bool:
        """
        Inicia un salto si el carrito no está ya saltando.
        Retorna True si el salto se inició, False si ya estaba en el aire.

        Secuencia (diagrama de flujo, sección movimiento):
            Si ESPACIO y NOT saltando:
                velocidad_salto = -fuerza_salto
                saltando = True
                color = color_salto
        """
        if self.saltando:
            return False
        self._vel_salto_actual = -self.fuerza_salto   # negativo = hacia arriba
        self.saltando          = True
        self.color_actual      = self.color_salto
        return True

    def moverse_y(self, direccion: Direccion) -> None:
        """
        Mueve el carrito en el eje Y según la flecha presionada.
        Respeta los límites superior e inferior de la carretera.

        Direccion.ARRIBA -> y disminuye (sube en pantalla)
        Direccion.ABAJO  -> y aumenta   (baja en pantalla)
        """
        if direccion == Direccion.ARRIBA:
            nueva_y = self.y - self.velocidad_y
            if nueva_y >= self.y_limite_superior:
                self.y       = nueva_y
                self.y_suelo = nueva_y       # actualizar suelo para aterrizaje
        elif direccion == Direccion.ABAJO:
            nueva_y = self.y + self.velocidad_y
            if nueva_y <= self.y_limite_inferior:
                self.y       = nueva_y
                self.y_suelo = nueva_y

    # Energía
    def recibir_danio(self, puntos: int) -> None:
        """
        Descuenta puntos de energía. Clampea a 0 (nunca negativo).
        """
        self.energia = max(0, self.energia - puntos)

    def porcentaje_energia(self) -> float:
        """Retorna energía como porcentaje [0.0 .. 1.0]."""
        return self.energia / self.energia_maxima

    def esta_vivo(self) -> bool:
        """True si el carrito aún tiene energía > 0."""
        return self.energia > 0

    # Colisiones (sin Pygame)
    def bbox(self, camara_x: float = 0.0, pixels_por_metro: float = 10.0) -> tuple[float, float, float, float]:
        """
        Bounding box del carrito en coordenadas MUNDO (metros/píxeles).
        Retorna (x_izq, y_top, x_der, y_bot) en píxeles de pantalla.

        camara_x: desplazamiento de cámara (metros) para convertir x mundo -> pantalla.
        pixels_por_metro: escala de conversión.
        """
        x_pantalla = (self.x - camara_x) * pixels_por_metro
        mitad_ancho = self.ancho / 2
        mitad_alto  = self.alto  / 2
        return (
            x_pantalla - mitad_ancho,
            self.y     - mitad_alto,
            x_pantalla + mitad_ancho,
            self.y     + mitad_alto,
        )

    def colisiona_con(
        self,
        obs_x1: float, obs_y1: float,
        obs_x2: float, obs_y2: float,
        camara_x: float = 0.0,
        pixels_por_metro: float = 10.0,
    ) -> bool:
        """
        Detección AABB (Axis-Aligned Bounding Box).
        Retorna True si el carrito se superpone con el rectángulo del obstáculo.

        Algoritmo AABB estándar:
            No hay colisión si alguna de estas condiciones es verdad:
                rect_A está completamente a la izquierda de rect_B
                rect_A está completamente a la derecha de rect_B
                rect_A está completamente arriba de rect_B
                rect_A está completamente abajo de rect_B
            De lo contrario: hay colisión.
        """
        cx1, cy1, cx2, cy2 = self.bbox(camara_x, pixels_por_metro)
        return not (cx2 <= obs_x1 or cx1 >= obs_x2 or cy2 <= obs_y1 or cy1 >= obs_y2)

    # Helpers internos
    def _aterrizar(self) -> None:
        """Lógica de aterrizaje: resetear estado de salto."""
        self.y                 = self.y_suelo
        self.saltando          = False
        self._vel_salto_actual = 0.0
        self.color_actual      = self.color_base

    # Representación
    def __repr__(self) -> str:
        estado = "SALTANDO" if self.saltando else "CORRIENDO"
        return (
            f"Carrito(x={self.x:.1f}m, y={self.y:.0f}px, "
            f"energia={self.energia}/{self.energia_maxima}, {estado})"
        )