"""
CLIRenderer — visualización del juego en terminal (sin Pygame).

Responsabilidades:
    - Dibujar el estado del juego frame a frame en la consola.
    - Mostrar la carretera, el carrito, los obstáculos y el HUD.
    - Renderizar el árbol AVL como diagrama ASCII nivel por nivel (BFS).
    - Mostrar recorridos en profundidad y anchura en formato legible.
    - Usar códigos ANSI para colores y formato (compatible con la mayoría
      de terminales modernas; se desactiva automáticamente en Windows CMD).

Sin dependencia de Pygame.
"""
from __future__ import annotations

import os
import sys
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_state import FrameState
    from data_structures.avl_node import NodoAVL

# ──────────────────────────────────────────────
# Detección de soporte ANSI
# ──────────────────────────────────────────────
_ANSI = (
    hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    or os.environ.get("FORCE_COLOR")
)

def _c(code: str, text: str) -> str:
    """Envuelve texto en código ANSI si el terminal lo soporta."""
    return f"\033[{code}m{text}\033[0m" if _ANSI else text

# Colores de conveniencia
def rojo(t: str)     -> str: return _c("91", t)
def verde(t: str)    -> str: return _c("92", t)
def amarillo(t: str) -> str: return _c("93", t)
def azul(t: str)     -> str: return _c("94", t)
def magenta(t: str)  -> str: return _c("95", t)
def cian(t: str)     -> str: return _c("96", t)
def blanco(t: str)   -> str: return _c("97", t)
def gris(t: str)     -> str: return _c("90", t)
def negrita(t: str)  -> str: return _c("1",  t)
def inverso(t: str)  -> str: return _c("7",  t)

# Iconos de tipos de obstáculo
ICONO_TIPO: dict[str, str] = {
    "ROCA":   "🪨",
    "BARRIL": "🛢",
    "CHARCO": "💧",
    "MURO":   "🧱",
    "CONO":   "🔺",
}

# Ancho de carretera en caracteres para el render CLI
CARRETERA_ANCHO = 80


class CLIRenderer:
    """
    Renderizador de texto plano para la simulación CLI del juego.

    Uso:
        renderer = CLIRenderer(ancho=80, limpiar_pantalla=True)
        renderer.dibujar_frame(frame_state)
    """

    def __init__(
        self,
        ancho:            int  = 80,
        limpiar_pantalla: bool = True,
        verbose:          bool = False,
    ) -> None:
        self.ancho            = min(ancho, shutil.get_terminal_size((80, 24)).columns)
        self.limpiar_pantalla = limpiar_pantalla
        self.verbose          = verbose

    # ─── Frame completo ──────────────────────────────────────────────
    def dibujar_frame(self, estado: "FrameState") -> None:
        """Dibuja un frame completo del estado actual del juego."""
        if self.limpiar_pantalla:
            self._limpiar()

        lineas: list[str] = []
        lineas += self._cabecera(estado)
        lineas += self._barra_progreso(estado)
        lineas += self._hud_energia(estado)
        lineas += self._carretera(estado)
        lineas += self._obstaculos_visibles(estado)
        lineas += self._pie(estado)

        print("\n".join(lineas))

    def dibujar_arbol(self, estado: "FrameState") -> None:
        """
        Dibuja el árbol AVL en ASCII usando BFS (niveles).
        Se invoca cuando mostrar_arbol=True en el FrameState.
        """
        print()
        print(negrita(azul("═" * self.ancho)))
        print(negrita(azul(f"{'ÁRBOL AVL DE OBSTÁCULOS':^{self.ancho}}")))
        print(negrita(azul("═" * self.ancho)))

        if not estado.niveles_arbol:
            print(gris("  (árbol vacío)"))
            return

        self._dibujar_niveles_bfs(estado.niveles_arbol)
        print()
        self._dibujar_recorridos(estado)

    def dibujar_resultado_final(self, estado: "FrameState") -> None:
        """Pantalla de victoria o derrota."""
        from core.enums import GameState
        if self.limpiar_pantalla:
            self._limpiar()

        if estado.estado_juego == GameState.VICTORIA:
            banner = verde
            titulo = "¡VICTORIA! 🏁"
            msg    = f"Recorriste {estado.carrito.x:.0f} m con {estado.carrito.energia}% de energía."
        else:
            banner = rojo
            titulo = "DERROTA 💀"
            msg    = f"El carrito se quedó sin energía en x={estado.carrito.x:.0f} m."

        borde = banner("█" * self.ancho)
        print(borde)
        print(banner(f"{'':^4}{titulo:^{self.ancho - 8}}{'':^4}"))
        print(banner(f"{'':^4}{msg:^{self.ancho - 8}}{'':^4}"))
        print(borde)
        print()
        print(negrita(f"  Total obstáculos procesados : {estado.total_nodos_avl}"))
        print(negrita(f"  Distancia recorrida         : {estado.carrito.x:.1f} / {estado.distancia_total_m} m"))
        print(negrita(f"  Energía final               : {estado.carrito.energia}%"))
        print()

    def dibujar_tick_log(
        self,
        tick:       int,
        estado:     "FrameState",
        colisiones: list,
    ) -> None:
        """
        Log de un tick individual (modo verbose).
        Muestra avance, colisiones y estado del carrito.
        """
        from core.enums import GameState
        prefijo = gris(f"[tick {tick:>4}]")
        x_str   = azul(f"x={estado.carrito.x:>7.1f}m")
        e_str   = self._color_energia(estado.carrito.energia)

        col_str = ""
        if colisiones:
            hits = ", ".join(
                f"{amarillo(o.tipo.value)}(-{o.danio})"
                for o in colisiones
            )
            col_str = f"  💥 {hits}"

        estado_str = ""
        if estado.estado_juego == GameState.VICTORIA:
            estado_str = verde("  ✓ META ALCANZADA")
        elif estado.estado_juego == GameState.DERROTA:
            estado_str = rojo("  ✗ SIN ENERGÍA")

        print(f"  {prefijo}  {x_str}  {e_str}{col_str}{estado_str}")

    # ─── Secciones del frame ─────────────────────────────────────────
    def _cabecera(self, estado: "FrameState") -> list[str]:
        from core.enums import GameState
        color = verde if estado.estado_juego == GameState.JUGANDO else rojo
        titulo = negrita(color(f"{'CARRITO AVL RUNNER — SIMULACIÓN CLI':^{self.ancho}}"))
        sep    = color("─" * self.ancho)
        return [sep, titulo, sep]

    def _barra_progreso(self, estado: "FrameState") -> list[str]:
        pct      = estado.porcentaje_progreso()
        relleno  = int(pct * (self.ancho - 14))
        vacio    = (self.ancho - 14) - relleno
        barra    = verde("█" * relleno) + gris("░" * vacio)
        pct_str  = f"{pct * 100:5.1f}%"
        return [f"  Progreso [{barra}] {pct_str}"]

    def _hud_energia(self, estado: "FrameState") -> list[str]:
        e   = estado.carrito.energia
        bar = self._barra_energia(e, ancho=30)
        salto = azul("↑SALTANDO") if estado.carrito.saltando else gris("EN SUELO ")
        pos   = f"x={azul(f'{estado.carrito.x:.1f}m')}  y={azul(f'{estado.carrito.y:.0f}px')}"
        return [f"  Energía {bar} {salto}   {pos}"]

    def _carretera(self, estado: "FrameState") -> list[str]:
        """
        Dibuja una representación ASCII simplificada de la carretera.
        Muestra al carrito y los obstáculos visibles en sus carriles.
        """
        # 3 carriles: ARRIBA (y~180), MEDIO (y~360), ABAJO (y~540)
        carriles = {
            "ARRIBA": 180,
            "MEDIO":  360,
            "ABAJO":  540,
        }
        ancho_vis = self.ancho - 4   # caracteres disponibles para la vista

        # Ventana visible: desde camara_x hasta camara_x + ancho_vis metros / escala
        pixels_por_metro = estado.pixels_por_metro
        vista_metros = ancho_vis / pixels_por_metro

        lineas = ["", gris("  ┌" + "─" * ancho_vis + "┐")]

        for nombre_carril, y_carril in carriles.items():
            fila = [" "] * ancho_vis

            # Dibujar obstáculos en este carril
            for obs in estado.obstaculos_visibles:
                if obs.eliminado:
                    continue
                # ¿El obstáculo pertenece a este carril?
                if abs(obs.y1 - y_carril) > 100:
                    continue

                # Posición relativa a la cámara en caracteres
                pos_rel = (obs.x1 - estado.camara_x) / vista_metros * ancho_vis
                col = int(pos_rel)
                if 0 <= col < ancho_vis:
                    icono = ICONO_TIPO.get(obs.tipo.value, "■")
                    # En terminales sin emoji, usar letra
                    fila[col] = obs.tipo.value[0]

            # Dibujar carrito si está en este carril
            carrito_y = estado.carrito.y
            if abs(carrito_y - y_carril) < 90:
                carrito_col = int(
                    (estado.carrito.x - estado.camara_x) / vista_metros * ancho_vis
                )
                carrito_col = max(0, min(carrito_col, ancho_vis - 3))
                simbolo = azul("[C]") if not estado.carrito.saltando else amarillo("[^]")
                fila[carrito_col]     = "["
                fila[carrito_col + 1] = "C" if not estado.carrito.saltando else "^"
                fila[carrito_col + 2] = "]"

            contenido  = "".join(fila)
            label = gris(f"{nombre_carril[:1]}")
            lineas.append(f"  │{label}{contenido[1:]}│")

        lineas.append(gris("  └" + "─" * ancho_vis + "┘"))
        return lineas

    def _obstaculos_visibles(self, estado: "FrameState") -> list[str]:
        activos = [o for o in estado.obstaculos_visibles if not o.eliminado]
        if not activos:
            return [gris("  (sin obstáculos en ventana)")]

        lineas = [gris(f"  Obstáculos visibles ({len(activos)}):")]
        for obs in activos[:6]:   # max 6 en pantalla
            icono = ICONO_TIPO.get(obs.tipo.value, "■")
            info  = (
                f"    {icono} {amarillo(obs.tipo.value):<8} "
                f"x=[{obs.x1}..{obs.x2}] "
                f"y=[{obs.y1}..{obs.y2}] "
                f"dmg={rojo(str(obs.danio))}"
            )
            lineas.append(info)
        return lineas

    def _pie(self, estado: "FrameState") -> list[str]:
        sep = gris("─" * self.ancho)
        controles = gris("  [↑↓] Mover  [ESPACIO] Saltar  [T] Ver árbol  [Q] Salir")
        nodos_info = gris(f"  Nodos AVL: {estado.total_nodos_avl}  |  "
                          f"FPS lógicos: {estado.fps_actual:.1f}")
        return [sep, controles, nodos_info, sep]

    # ─── Árbol AVL ASCII ─────────────────────────────────────────────
    def _dibujar_niveles_bfs(self, niveles: list[list["NodoAVL"]]) -> None:
        """
        Dibuja el árbol nivel por nivel usando BFS.
        Cada nodo muestra: tipo + coordenada (x,y) + factor de balance.

        Algoritmo de espaciado:
            El ancho máximo del nivel hoja determina el espaciado de niveles
            superiores (árbol "dibujado desde abajo hacia arriba").
        """
        MAX_NIVELES = 6   # más niveles empiezan a desbordar la pantalla
        niveles_vis = niveles[:MAX_NIVELES]
        n_niveles   = len(niveles_vis)

        for idx, nivel in enumerate(niveles_vis):
            espacio_entre = max(1, (self.ancho - 2) // (len(nivel) + 1))
            profundidad   = n_niveles - idx - 1

            # Construir fila de nodos
            partes_nodo = []
            for nodo in nivel:
                x, y    = nodo.clave()
                tipo    = nodo.obstaculo.tipo.value[:3]
                fb      = nodo.factor_balance
                fb_str  = verde(f"fb{fb:+d}") if fb == 0 else amarillo(f"fb{fb:+d}")
                etiqueta = f"{tipo}({x},{y})[{fb_str}]"
                partes_nodo.append(etiqueta)

            fila = (" " * espacio_entre).join(partes_nodo)
            indent = " " * max(0, (self.ancho - len(fila)) // 2)
            nivel_label = gris(f"N{idx}")
            print(f"  {nivel_label} {indent}{fila}")

            # Conectores hacia los hijos (solo si no es el último nivel)
            if idx < n_niveles - 1:
                conectores = []
                for nodo in nivel:
                    tiene_izq = nodo.izquierdo is not None
                    tiene_der = nodo.derecho   is not None
                    if tiene_izq and tiene_der:
                        conectores.append(gris("┴"))
                    elif tiene_izq:
                        conectores.append(gris("┘"))
                    elif tiene_der:
                        conectores.append(gris("└"))
                    else:
                        conectores.append(" ")
                fila_con = (" " * espacio_entre).join(conectores)
                print(f"     {indent}{fila_con}")

        if len(niveles) > MAX_NIVELES:
            print(gris(f"  ... ({len(niveles) - MAX_NIVELES} niveles más no mostrados)"))

    def _dibujar_recorridos(self, estado: "FrameState") -> None:
        """Imprime los recorridos disponibles del árbol."""
        recorridos = {
            "BFS (anchura)":   "bfs",
            "Inorden":         "inorden",
            "Preorden":        "preorden",
            "Postorden":       "postorden",
        }

        # Resaltar el recorrido activo
        actual = estado.recorrido_actual

        for nombre, clave in recorridos.items():
            if estado.recorrido_lista and clave == actual:
                elementos = " → ".join(
                    f"{o.tipo.value}({o.x1},{o.y1})"
                    for o in estado.recorrido_lista[:12]
                )
                sufijo = " ..." if len(estado.recorrido_lista) > 12 else ""
                print(f"  {negrita(verde(f'▶ {nombre}:'))}")
                print(f"    {verde(elementos)}{sufijo}")
            else:
                print(gris(f"    {nombre}"))

    # ─── Helpers de color ────────────────────────────────────────────
    def _barra_energia(self, energia: int, ancho: int = 20) -> str:
        pct     = energia / 100
        relleno = int(pct * ancho)
        vacio   = ancho - relleno
        if pct > 0.6:
            col = verde
        elif pct > 0.3:
            col = amarillo
        else:
            col = rojo
        barra = col("█" * relleno) + gris("░" * vacio)
        return f"[{barra}] {self._color_energia(energia)}"

    def _color_energia(self, energia: int) -> str:
        txt = f"E={energia:>3}%"
        if energia > 60:
            return verde(txt)
        elif energia > 30:
            return amarillo(txt)
        return rojo(txt)

    # ─── Utilidades ──────────────────────────────────────────────────
    def _limpiar(self) -> None:
        """Limpia la pantalla del terminal."""
        os.system("cls" if os.name == "nt" else "clear")

    def imprimir_bienvenida(self, config: dict) -> None:
        """Banner de inicio del juego."""
        print()
        print(negrita(cian("╔" + "═" * (self.ancho - 2) + "╗")))
        print(negrita(cian(f"║{'CARRITO AVL RUNNER':^{self.ancho - 2}}║")))
        print(negrita(cian(f"║{'Simulación CLI — Fase 3':^{self.ancho - 2}}║")))
        print(negrita(cian("╚" + "═" * (self.ancho - 2) + "╝")))
        print()
        print(negrita("  Configuración cargada:"))
        for k, v in config.items():
            print(gris(f"    {k:<30} = {v}"))
        print()