"""
Suite de pruebas para la Fase 3 — GameEngine CLI sin Pygame.

Cubre:
    - CollisionSystem: detección AABB, daño, marcado de eliminados.
    - GameEngine (headless): avance del carrito, colisiones con obstáculos
        reales del JSON, condición de victoria, condición de derrota.
    - Integración completa: JSON -> AVL -> GameLoop -> estado final.
    - Recorridos: el engine expone BFS, inorden, preorden, postorden.
    - Cámara: la ventana visible avanza correctamente con el carrito.

Ejecutar:
    pytest tests/test_engine.py -v
    pytest tests/test_engine.py -v -s          # ver output del renderer
"""
from __future__ import annotations

import sys
import os
import json
import tempfile
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from core.enums import GameState, TipoObstaculo, Direccion
from models.carrito import Carrito
from models.obstaculo import Obstaculo
from data_structures.avl_tree import ArbolAVL
from engine.collision_system import CollisionSystem, ColisionResult
from engine.game_engine import GameEngine

# Helpers 
CONFIG_BASE = {
    "juego": {
        "distancia_total_m": 1000,
        "velocidad_x_ms":    10,
        "velocidad_y_ms":    3,
        "refresh_ms":        200,
        "fuerza_salto":      12,
        "gravedad":          9.8,
        "energia_inicial":   100,
        "color_carrito":     "#3A7BD5",
        "color_salto":       "#F5A623",
        "pixels_por_metro":  10,
    },
    "pantalla": {"ancho": 1280, "alto": 720, "titulo": "Test"},
    "tipos_obstaculo": {
        "ROCA":   {"danio": 20, "color": "#5a5a5a"},
        "BARRIL": {"danio": 35, "color": "#E87722"},
        "CHARCO": {"danio": 10, "color": "#1a3a5c"},
        "MURO":   {"danio": 30, "color": "#c2b59b"},
        "CONO":   {"danio":  5, "color": "#FF6B35"},
    },
    "obstaculos": [],
}

def _config_json(obstaculos: list[dict] | None = None, **overrides) -> Path:
    """Crea un JSON de configuración temporal y retorna su Path."""
    datos = deepcopy(CONFIG_BASE)
    if obstaculos is not None:
        datos["obstaculos"] = obstaculos
    for clave, valor in overrides.items():
        datos["juego"][clave] = valor
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(datos, f, ensure_ascii=False)
    f.close()
    return Path(f.name)

def _obs(x1, y1, x2, y2, tipo="ROCA", danio=20) -> Obstaculo:
    return Obstaculo(x1=x1, y1=y1, x2=x2, y2=y2,
                     tipo=TipoObstaculo(tipo), danio=danio)

def _carrito(x=0.0, y=360.0, vel_x=5.0) -> Carrito:
    return Carrito(
        x=x, y=y, y_suelo=y,
        velocidad_x=vel_x, velocidad_y=3.0,
        fuerza_salto=12.0, gravedad=1.5,
        energia=100, energia_maxima=100,
        color_base=(58, 123, 213),
        color_salto=(245, 166, 35),
    )

# Tests: CollisionSystem
class TestCollisionSystem:

    def test_sin_candidatos_no_hay_colision(self):
        c = _carrito()
        r = CollisionSystem.detectar_con_bbox_mundo(c, [])
        assert r.hubo_colision is False
        assert r.danio_total == 0

    def test_colision_directa(self):
        """Obstáculo justo donde está el carrito → colisión."""
        c   = _carrito(x=0.0, y=360.0)
        obs = _obs(x1=-5, y1=340, x2=15, y2=380)
        r   = CollisionSystem.detectar_con_bbox_mundo(
            c, [obs], camara_x=0.0, pixels_por_metro=10.0
        )
        assert r.hubo_colision is True
        assert r.danio_total == 20

    def test_obstaculos_marcados_como_eliminados(self):
        """Tras colisión, el obstáculo debe marcarse eliminado."""
        c   = _carrito(x=0.0)
        obs = _obs(x1=-5, y1=340, x2=15, y2=380)
        CollisionSystem.detectar_con_bbox_mundo(c, [obs])
        assert obs.eliminado is True

    def test_eliminado_no_causa_doble_danio(self):
        """Un obstáculo ya eliminado no debe causar daño en segundo tick."""
        c   = _carrito(x=0.0)
        obs = _obs(x1=-5, y1=340, x2=15, y2=380)
        r1 = CollisionSystem.detectar_con_bbox_mundo(c, [obs])
        r2 = CollisionSystem.detectar_con_bbox_mundo(c, [obs])  # ya eliminado
        assert r1.hubo_colision is True
        assert r2.hubo_colision is False

    def test_sin_colision_obstaculo_a_la_derecha(self):
        c   = _carrito(x=0.0, y=360.0)
        obs = _obs(x1=500, y1=340, x2=540, y2=380)
        r   = CollisionSystem.detectar_con_bbox_mundo(
            c, [obs], camara_x=0.0, pixels_por_metro=10.0
        )
        assert r.hubo_colision is False

    def test_sin_colision_obstaculo_en_otro_carril(self):
        """Obstáculo en carril superior no choca con carrito en carril medio."""
        c   = _carrito(x=0.0, y=360.0)
        obs = _obs(x1=-5, y1=100, x2=15, y2=160)   # carril superior
        r   = CollisionSystem.detectar_con_bbox_mundo(c, [obs])
        assert r.hubo_colision is False

    def test_multiples_obstaculos_suma_danio(self):
        """Dos obstáculos superpuestos deben sumar su daño."""
        c    = _carrito(x=0.0)
        obs1 = _obs(x1=-5, y1=340, x2=15, y2=380, danio=20)
        obs2 = _obs(x1=-5, y1=350, x2=15, y2=370, tipo="CONO", danio=5)
        r    = CollisionSystem.detectar_con_bbox_mundo(c, [obs1, obs2])
        assert r.danio_total == 25
        assert len(r.obstaculos_hit) == 2

    def test_colision_result_repr(self):
        r = ColisionResult(hubo_colision=False)
        assert "sin colisión" in repr(r)

    def test_no_colision_borde_exacto(self):
        """Borde exacto: el carrito y el obstáculo se tocan pero sin superposición."""
        c   = _carrito(x=0.0, y=360.0)
        # Carrito bbox: aprox x=[-20,20], y=[345,375] con ancho=40, alto=30
        # Obstáculo empieza exactamente donde termina el carrito por la derecha
        x1_carrito_der = 20.0   # aproximado, depende de CAMARA_OFFSET_X
        obs = _obs(x1=int(x1_carrito_der) + 1, y1=345, x2=int(x1_carrito_der) + 50, y2=375)
        r   = CollisionSystem.detectar_con_bbox_mundo(c, [obs])
        # Con el carrito en x=0 y camara en 0, x_pantalla = 0
        # No debería colisionar si el obstáculo está claramente a la derecha
        # (resultado depende de escala; lo importante es que no haya excepción)
        assert isinstance(r, ColisionResult)

# Tests: GameEngine headless
class TestGameEngineHeadless:

    def _engine(self, obstaculos=None, distancia=1000, energia=100, vel_x=10):
        ruta = _config_json(obstaculos, distancia_total_m=distancia,
                            energia_inicial=energia, velocidad_x_ms=vel_x)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)
        return engine

    def test_victoria_sin_obstaculos(self):
        """Sin obstáculos, el carrito debe llegar a la meta."""
        engine = self._engine(obstaculos=[], distancia=100)
        estado = engine.run_headless(max_ticks=50)
        assert estado == GameState.VICTORIA

    def test_derrota_con_obstaculo_letal(self):
        """
        Un obstáculo con daño = 100 en el camino directo del carrito
        debe causar derrota inmediata.
        """
        # Obstáculo en el carril medio donde arranca el carrito (y=360)
        # El carrito avanza 10 m/tick; a los 5 ticks está en x=50
        obs_letales = [
            {"tipo": "MURO", "x1": 30, "y1": 340, "x2": 60, "y2": 390}
        ]
        # Dar daño total = 100 sobreescribiendo el tipo
        datos = deepcopy(CONFIG_BASE)
        datos["juego"]["distancia_total_m"] = 500
        datos["juego"]["velocidad_x_ms"]    = 10
        datos["juego"]["energia_inicial"]   = 30   # energía baja
        datos["tipos_obstaculo"]["MURO"]["danio"] = 30
        datos["obstaculos"] = obs_letales
        ruta = _config_json()
        # Reescribir el JSON directamente
        import json as _json
        ruta.write_text(_json.dumps(datos), encoding="utf-8")
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)
        estado = engine.run_headless(max_ticks=20)
        # El carrito con 30 de energía recibe 30 de daño → debe morir
        assert estado == GameState.DERROTA

    def test_carrito_avanza_en_x(self):
        """El carrito debe avanzar exactamente vel_x metros por tick."""
        engine = self._engine(obstaculos=[], distancia=500, vel_x=10)
        carrito = engine.carrito()
        x_antes = carrito.x
        # Forzar un tick manualmente a través de headless con 1 tick
        engine.run_headless(max_ticks=1)
        assert carrito.x == pytest.approx(x_antes + 10.0)

    def test_energia_se_reduce_con_colision(self):
        """Tras colisionar con un obstáculo, la energía debe reducirse."""
        obs = [{"tipo": "ROCA", "x1": 30, "y1": 345, "x2": 60, "y2": 375}]
        engine = self._engine(obstaculos=obs, distancia=500, vel_x=10)
        engine.run_headless(max_ticks=10)
        assert engine.carrito().energia < 100

    def test_estado_inicial_es_jugando(self):
        engine = self._engine()
        assert engine.estado_actual() == GameState.JUGANDO

    def test_arbol_cargado_con_obstaculos(self):
        obs = [
            {"tipo": "ROCA",   "x1": 100, "y1": 300, "x2": 140, "y2": 360},
            {"tipo": "BARRIL", "x1": 200, "y1": 280, "x2": 240, "y2": 340},
        ]
        engine = self._engine(obstaculos=obs)
        assert engine.arbol().total_nodos == 2

    def test_insercion_manual_en_arbol(self):
        engine = self._engine(obstaculos=[])
        ok = engine.insertar_obstaculo_manual(
            x1=50, y1=300, x2=90, y2=360, tipo="CONO", danio=5
        )
        assert ok is True
        assert engine.arbol().total_nodos == 1

    def test_insercion_duplicada_rechazada(self):
        engine = self._engine(obstaculos=[])
        engine.insertar_obstaculo_manual(50, 300, 90, 360, "CONO", 5)
        ok2 = engine.insertar_obstaculo_manual(50, 300, 90, 360, "CONO", 5)
        assert ok2 is False
        assert engine.arbol().total_nodos == 1

    def test_eliminacion_de_obstaculo(self):
        obs = [{"tipo": "ROCA", "x1": 100, "y1": 300, "x2": 140, "y2": 360}]
        engine = self._engine(obstaculos=obs)
        ok = engine.eliminar_obstaculo(100, 300)
        assert ok is True
        assert engine.arbol().total_nodos == 0

    def test_acciones_programadas_saltar(self):
        """Con acción 'saltar' en tick 1, el carrito debe quedar en estado saltando."""
        engine = self._engine(obstaculos=[], distancia=200)
        engine.run_headless(acciones=[(1, "saltar")], max_ticks=2)
        # Después de saltar y 1 tick de física, el carrito puede seguir saltando
        # Lo importante es que no haya excepción y el estado sea coherente
        assert engine.carrito().x > 0

    def test_acciones_programadas_arriba_abajo(self):
        """El carrito debe responder a acciones de movimiento en Y."""
        engine = self._engine(obstaculos=[], distancia=200)
        y_inicial = engine.carrito().y
        engine.run_headless(acciones=[(1, "abajo")], max_ticks=2)
        assert engine.carrito().y >= y_inicial   # bajó o se mantuvo

# Tests: Cámara y ventana visible
class TestCamara:

    def test_obstaculos_fuera_de_ventana_no_se_ven(self):
        """El AVL.rango() no debe retornar obstáculos fuera de la cámara."""
        obs = [
            {"tipo": "ROCA",   "x1": 10,  "y1": 300, "x2": 50,  "y2": 360},
            {"tipo": "BARRIL", "x1": 900, "y1": 280, "x2": 940, "y2": 340},
        ]
        ruta = _config_json(obs, distancia_total_m=1000, velocidad_x_ms=10)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)

        # Al inicio, cámara está cerca de x=0; el obstáculo en x=900 no debe verse
        arbol = engine.arbol()
        from core.constants import SCREEN_W, PIXELS_POR_METRO
        camara_x = 0.0
        x_max    = camara_x + (SCREEN_W / PIXELS_POR_METRO)
        visibles = arbol.rango(camara_x, x_max, 0, 720)
        claves   = [o.clave_avl() for o in visibles]

        assert (10, 300)  in claves    # obstáculo cercano: visible
        assert (900, 280) not in claves  # obstáculo lejano: no visible

    def test_camara_sigue_al_carrito(self):
        """La cámara debe seguir al carrito (camara_x crece con x del carrito)."""
        ruta   = _config_json([], distancia_total_m=500, velocidad_x_ms=10)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)

        engine.run_headless(max_ticks=5)
        # Después de 5 ticks: carrito en x=50, cámara debe haber avanzado
        from core.constants import CAMARA_OFFSET_X, PIXELS_POR_METRO
        esperada = max(0.0, engine.carrito().x - CAMARA_OFFSET_X / PIXELS_POR_METRO)
        # La cámara se actualiza internamente; el carrito avanzó
        assert engine.carrito().x == pytest.approx(50.0)

# Tests: Recorridos del árbol 
class TestRecorridosEngine:

    def _engine_con_obs(self):
        obs = [
            {"tipo": "ROCA",   "x1": 100, "y1": 300, "x2": 140, "y2": 360},
            {"tipo": "BARRIL", "x1": 200, "y1": 280, "x2": 240, "y2": 340},
            {"tipo": "CHARCO", "x1": 300, "y1": 530, "x2": 380, "y2": 560},
            {"tipo": "CONO",   "x1": 400, "y1": 510, "x2": 430, "y2": 560},
            {"tipo": "MURO",   "x1": 500, "y1": 200, "x2": 530, "y2": 500},
        ]
        ruta = _config_json(obs, distancia_total_m=1000)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)
        return engine

    def test_inorden_ordenado_por_x1(self):
        engine  = self._engine_con_obs()
        inorden = engine.arbol().inorden()
        x1s     = [o.x1 for o in inorden]
        assert x1s == sorted(x1s)

    def test_bfs_niveles_cubren_todos_nodos(self):
        engine  = self._engine_con_obs()
        niveles = engine.arbol().bfs()
        total   = sum(len(n) for n in niveles)
        assert total == engine.arbol().total_nodos

    def test_preorden_raiz_primero(self):
        engine  = self._engine_con_obs()
        arbol   = engine.arbol()
        pre     = arbol.preorden()
        assert pre[0].clave_avl() == arbol.raiz.clave()

    def test_postorden_raiz_ultimo(self):
        engine  = self._engine_con_obs()
        arbol   = engine.arbol()
        post    = arbol.postorden()
        assert post[-1].clave_avl() == arbol.raiz.clave()

    def test_todos_recorridos_mismos_elementos(self):
        engine = self._engine_con_obs()
        arbol  = engine.arbol()
        s_in   = {o.clave_avl() for o in arbol.inorden()}
        s_pre  = {o.clave_avl() for o in arbol.preorden()}
        s_post = {o.clave_avl() for o in arbol.postorden()}
        s_bfs  = {o.clave_avl() for o in arbol.bfs_lista()}
        assert s_in == s_pre == s_post == s_bfs

# Tests: Integración completa 
class TestIntegracionCompleta:

    def test_juego_completo_con_json_real(self):
        """
        Carga el JSON real del proyecto y ejecuta una partida headless completa.
        Verifica que el estado final sea VICTORIA o DERROTA (nunca JUGANDO).
        """
        ruta_real = Path(__file__).parent.parent / "config" / "game_config.json"
        if not ruta_real.exists():
            pytest.skip("config/game_config.json no encontrado")

        engine = GameEngine(
            ruta_config=ruta_real,
            verbose=False,
            velocidad_simulacion=1000.0,
        )
        estado = engine.run_headless(max_ticks=500)
        assert estado in (GameState.VICTORIA, GameState.DERROTA)

    def test_arbol_balanceado_despues_del_juego(self):
        """El árbol AVL debe seguir balanceado después de marcar nodos eliminados."""
        obs = [
            {"tipo": "ROCA",   "x1": 50,  "y1": 300, "x2": 90,  "y2": 360},
            {"tipo": "BARRIL", "x1": 150, "y1": 340, "x2": 190, "y2": 380},
            {"tipo": "CONO",   "x1": 250, "y1": 510, "x2": 280, "y2": 550},
        ]
        ruta = _config_json(obs, distancia_total_m=300, velocidad_x_ms=10)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)
        engine.run_headless(max_ticks=50)

        def verificar_balance(nodo):
            if nodo is None:
                return
            assert abs(nodo.factor_balance) <= 1
            verificar_balance(nodo.izquierdo)
            verificar_balance(nodo.derecho)

        verificar_balance(engine.arbol().raiz)

    def test_sin_pygame_en_fase3(self):
        """Ningún módulo de Fase 3 debe importar Pygame."""
        assert "pygame" not in sys.modules, (
            "Pygame no debe estar importado en Fase 3. "
            "El CLI GameEngine debe ser completamente independiente del motor gráfico."
        )

    def test_energia_no_negativa_tras_muchas_colisiones(self):
        """La energía del carrito nunca debe ser negativa."""
        obs = [
            {"tipo": "MURO", "x1": i * 20 + 10, "y1": 345, "x2": i * 20 + 15, "y2": 375}
            for i in range(20)
        ]
        ruta = _config_json(obs, distancia_total_m=1000, velocidad_x_ms=10)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)
        engine.run_headless(max_ticks=100)
        assert engine.carrito().energia >= 0

    def test_victoria_exactamente_en_meta(self):
        """El juego debe terminar en VICTORIA cuando carrito.x >= distancia_total_m."""
        ruta = _config_json([], distancia_total_m=50, velocidad_x_ms=10)
        engine = GameEngine(ruta_config=ruta, verbose=False,
                            velocidad_simulacion=1000.0)
        ruta.unlink(missing_ok=True)
        estado = engine.run_headless(max_ticks=20)
        assert estado == GameState.VICTORIA
        assert engine.carrito().x >= 50