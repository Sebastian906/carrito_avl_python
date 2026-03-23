"""
Suite completa de pruebas para la Fase 2.

Cubre:
    - ConfigLoader: carga correcta, validaciones descriptivas, acceso por clave.
    - hex_a_rgb: conversión de colores.
    - obstaculos(): construcción de Obstaculo desde JSON, inserción en ArbolAVL.
    - Carrito: movimiento en X, control en Y, salto con física, energía, AABB.
    - FrameState: construcción y helpers.
    - Integración: JSON -> ConfigLoader -> ArbolAVL.rango().

Ejecutar: pytest tests/test_config.py -v
"""
import sys
import os
import json
import tempfile
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from utils.config_loader import ConfigLoader, ConfigError
from models.carrito import Carrito
from models.obstaculo import Obstaculo
from models.game_state import FrameState
from data_structures.avl_tree import ArbolAVL
from core.enums import TipoObstaculo, Direccion, GameState

# FIXTURES
CONFIG_VALIDO = {
    "juego": {
        "distancia_total_m": 1000,
        "velocidad_x_ms":    5,
        "velocidad_y_ms":    3,
        "refresh_ms":        200,
        "fuerza_salto":      12,
        "gravedad":          9.8,
        "energia_inicial":   100,
        "color_carrito":     "#3A7BD5",
        "color_salto":       "#F5A623",
        "pixels_por_metro":  10,
    },
    "pantalla": {
        "ancho":  1280,
        "alto":   720,
        "titulo": "Test Runner",
    },
    "tipos_obstaculo": {
        "ROCA":   {"danio": 20, "color": "#5a5a5a"},
        "BARRIL": {"danio": 35, "color": "#E87722"},
        "CHARCO": {"danio": 10, "color": "#1a3a5c"},
        "MURO":   {"danio": 30, "color": "#c2b59b"},
        "CONO":   {"danio":  5, "color": "#FF6B35"},
    },
    "obstaculos": [
        {"tipo": "ROCA",   "x1": 100, "y1": 300, "x2": 140, "y2": 360},
        {"tipo": "BARRIL", "x1": 250, "y1": 280, "x2": 290, "y2": 340},
        {"tipo": "CHARCO", "x1": 350, "y1": 530, "x2": 430, "y2": 560},
    ],
}

def _json_temporal(datos: dict) -> Path:
    """Escribe un dict como JSON en un archivo temporal y retorna su Path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(datos, f, ensure_ascii=False)
    f.close()
    return Path(f.name)

@pytest.fixture
def config_valido() -> ConfigLoader:
    """ConfigLoader ya cargado con CONFIG_VALIDO."""
    ruta = _json_temporal(CONFIG_VALIDO)
    c = ConfigLoader()
    c.cargar(ruta)
    ruta.unlink(missing_ok=True)
    return c

@pytest.fixture
def carrito_base() -> Carrito:
    """Carrito en posición inicial estándar."""
    return Carrito(
        x=0.0, y=360.0, y_suelo=360.0,
        velocidad_x=5.0, velocidad_y=3.0,
        fuerza_salto=12.0, gravedad=1.5,  # gravedad baja para tests controlados
        energia=100, energia_maxima=100,
        color_base=(58, 123, 213),
        color_salto=(245, 166, 35),
    )

# TESTS: ConfigLoader — carga correcta
class TestConfigLoaderCarga:

    def test_carga_archivo_valido(self, config_valido):
        assert config_valido is not None

    def test_archivo_no_existente_lanza_error(self):
        c = ConfigLoader()
        with pytest.raises(FileNotFoundError, match="no encontrado"):
            c.cargar("ruta/que/no/existe.json")

    def test_json_invalido_lanza_error(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        f.write("{esto no es json válido")
        f.close()
        c = ConfigLoader()
        with pytest.raises(ConfigError, match="no es JSON válido"):
            c.cargar(f.name)
        Path(f.name).unlink(missing_ok=True)

    def test_acceder_sin_cargar_lanza_runtime(self):
        c = ConfigLoader()
        with pytest.raises(RuntimeError, match="cargar"):
            c.get("juego.refresh_ms")

    def test_repr_sin_cargar(self):
        c = ConfigLoader()
        assert "sin cargar" in repr(c)

    def test_repr_cargado(self, config_valido):
        assert "ConfigLoader(" in repr(config_valido)

# TESTS: ConfigLoader — acceso get()
class TestConfigLoaderGet:

    def test_get_juego_refresh_ms(self, config_valido):
        assert config_valido.get("juego.refresh_ms") == 200

    def test_get_pantalla_ancho(self, config_valido):
        assert config_valido.get("pantalla.ancho") == 1280

    def test_get_clave_inexistente_retorna_default(self, config_valido):
        assert config_valido.get("juego.campo_inventado", 42) == 42

    def test_get_juego_atajo(self, config_valido):
        assert config_valido.get_juego("velocidad_x_ms") == 5

    def test_get_pantalla_atajo(self, config_valido):
        assert config_valido.get_pantalla("alto") == 720

    def test_get_distancia_total(self, config_valido):
        assert config_valido.get("juego.distancia_total_m") == 1000

    def test_get_energia_inicial(self, config_valido):
        assert config_valido.get_juego("energia_inicial") == 100

# TESTS: ConfigLoader — colores
class TestConfigLoaderColores:

    def test_hex_a_rgb_correcto(self):
        assert ConfigLoader.hex_a_rgb("#3A7BD5") == (58, 123, 213)

    def test_hex_a_rgb_minusculas(self):
        assert ConfigLoader.hex_a_rgb("#5a5a5a") == (90, 90, 90)

    def test_hex_a_rgb_blanco(self):
        assert ConfigLoader.hex_a_rgb("#FFFFFF") == (255, 255, 255)

    def test_hex_a_rgb_negro(self):
        assert ConfigLoader.hex_a_rgb("#000000") == (0, 0, 0)

    def test_hex_a_rgb_formato_invalido(self):
        with pytest.raises(ValueError, match="Color inválido"):
            ConfigLoader.hex_a_rgb("3A7BD5")     # sin #

    def test_hex_a_rgb_longitud_incorrecta(self):
        with pytest.raises(ValueError):
            ConfigLoader.hex_a_rgb("#3A7B")       # muy corto

    def test_color_carrito(self, config_valido):
        r, g, b = config_valido.color_carrito()
        assert isinstance(r, int) and 0 <= r <= 255

    def test_color_salto(self, config_valido):
        r, g, b = config_valido.color_salto()
        assert isinstance(r, int) and 0 <= r <= 255

    def test_color_tipo_roca(self, config_valido):
        assert config_valido.color_tipo("ROCA") == (90, 90, 90)

# TESTS: ConfigLoader — validaciones (errores descriptivos)
class TestConfigLoaderValidaciones:

    def _cargar_modificado(self, modificaciones: dict) -> None:
        """Helper: carga CONFIG_VALIDO con las modificaciones aplicadas."""
        datos = deepcopy(CONFIG_VALIDO)
        for ruta_clave, valor in modificaciones.items():
            partes = ruta_clave.split(".")
            ref = datos
            for p in partes[:-1]:
                ref = ref[p]
            if valor is None:
                ref.pop(partes[-1], None)
            else:
                ref[partes[-1]] = valor
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        try:
            c.cargar(ruta)
        finally:
            ruta.unlink(missing_ok=True)

    def test_falta_distancia_total(self):
        with pytest.raises(ConfigError, match="distancia_total_m"):
            self._cargar_modificado({"juego.distancia_total_m": None})

    def test_distancia_negativa(self):
        with pytest.raises(ConfigError, match="distancia_total_m"):
            self._cargar_modificado({"juego.distancia_total_m": -10})

    def test_refresh_ms_demasiado_bajo(self):
        with pytest.raises(ConfigError, match="refresh_ms"):
            self._cargar_modificado({"juego.refresh_ms": 5})

    def test_energia_inicial_cero(self):
        with pytest.raises(ConfigError, match="energia_inicial"):
            self._cargar_modificado({"juego.energia_inicial": 0})

    def test_energia_inicial_mayor_100(self):
        with pytest.raises(ConfigError, match="energia_inicial"):
            self._cargar_modificado({"juego.energia_inicial": 150})

    def test_color_carrito_invalido(self):
        with pytest.raises(ConfigError, match="color_carrito"):
            self._cargar_modificado({"juego.color_carrito": "azul"})

    def test_tipo_obstaculo_faltante(self):
        datos = deepcopy(CONFIG_VALIDO)
        del datos["tipos_obstaculo"]["ROCA"]
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        with pytest.raises(ConfigError, match="ROCA"):
            c.cargar(ruta)
        ruta.unlink(missing_ok=True)

    def test_danio_negativo_en_tipo(self):
        datos = deepcopy(CONFIG_VALIDO)
        datos["tipos_obstaculo"]["CONO"]["danio"] = -5
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        with pytest.raises(ConfigError, match="danio"):
            c.cargar(ruta)
        ruta.unlink(missing_ok=True)

    def test_obstaculo_x1_mayor_x2(self):
        datos = deepcopy(CONFIG_VALIDO)
        datos["obstaculos"][0]["x1"] = 200
        datos["obstaculos"][0]["x2"] = 100
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        with pytest.raises(ConfigError, match="x1"):
            c.cargar(ruta)
        ruta.unlink(missing_ok=True)

    def test_obstaculo_tipo_invalido(self):
        datos = deepcopy(CONFIG_VALIDO)
        datos["obstaculos"][0]["tipo"] = "PLATANO"
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        with pytest.raises(ConfigError, match="PLATANO"):
            c.cargar(ruta)
        ruta.unlink(missing_ok=True)

    def test_multiples_errores_en_un_solo_mensaje(self):
        """Todos los errores deben aparecer juntos, no uno por ejecución."""
        datos = deepcopy(CONFIG_VALIDO)
        datos["juego"]["energia_inicial"] = -10
        datos["juego"]["refresh_ms"]      = 1
        datos["juego"]["color_carrito"]   = "mal_color"
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        with pytest.raises(ConfigError) as exc_info:
            c.cargar(ruta)
        msg = str(exc_info.value)
        # Los tres errores deben estar en el mismo mensaje
        assert "energia_inicial" in msg
        assert "refresh_ms"      in msg
        assert "color_carrito"   in msg
        ruta.unlink(missing_ok=True)

    def test_obstaculo_campo_faltante(self):
        datos = deepcopy(CONFIG_VALIDO)
        del datos["obstaculos"][0]["x2"]
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        with pytest.raises(ConfigError, match="x2"):
            c.cargar(ruta)
        ruta.unlink(missing_ok=True)

# TESTS: ConfigLoader — obstaculos()
class TestConfigLoaderObstaculos:

    def test_cantidad_correcta(self, config_valido):
        obs = config_valido.obstaculos()
        assert len(obs) == 3

    def test_son_instancias_obstaculo(self, config_valido):
        for o in config_valido.obstaculos():
            assert isinstance(o, Obstaculo)

    def test_danio_tomado_de_tipos(self, config_valido):
        obs = config_valido.obstaculos()
        roca = next(o for o in obs if o.tipo == TipoObstaculo.ROCA)
        assert roca.danio == 20    # según CONFIG_VALIDO

    def test_ordenados_por_x1(self, config_valido):
        obs = config_valido.obstaculos()
        x1s = [o.x1 for o in obs]
        assert x1s == sorted(x1s)

    def test_no_eliminados_por_defecto(self, config_valido):
        for o in config_valido.obstaculos():
            assert o.eliminado is False

    def test_duplicado_ignorado_con_aviso(self, capsys):
        datos = deepcopy(CONFIG_VALIDO)
        # Agregar un duplicado exacto del primer obstáculo
        datos["obstaculos"].append(
            {"tipo": "ROCA", "x1": 100, "y1": 300, "x2": 140, "y2": 360}
        )
        ruta = _json_temporal(datos)
        c = ConfigLoader()
        c.cargar(ruta)
        obs = c.obstaculos()
        salida = capsys.readouterr().out
        ruta.unlink(missing_ok=True)
        assert len(obs) == 3             # el duplicado se ignoró
        assert "duplicada" in salida.lower() or "AVISO" in salida

# TESTS: Carrito — movimiento en X
class TestCarritoMovimientoX:

    def test_avanza_automaticamente(self, carrito_base):
        x_inicial = carrito_base.x
        carrito_base.actualizar(dt=1.0)
        assert carrito_base.x == x_inicial + carrito_base.velocidad_x

    def test_avanza_proporcional_a_dt(self, carrito_base):
        carrito_base.actualizar(dt=2.0)
        assert carrito_base.x == pytest.approx(carrito_base.velocidad_x * 2)

    def test_posicion_inicial(self, carrito_base):
        assert carrito_base.x == 0.0

    def test_multiples_ticks(self, carrito_base):
        for _ in range(10):
            carrito_base.actualizar(dt=1.0)
        assert carrito_base.x == pytest.approx(50.0)   # 5 m/tick * 10 ticks

# TESTS: Carrito — control en Y
class TestCarritoMovimientoY:

    def test_moverse_arriba(self, carrito_base):
        y_inicial = carrito_base.y
        carrito_base.moverse_y(Direccion.ARRIBA)
        assert carrito_base.y < y_inicial

    def test_moverse_abajo(self, carrito_base):
        y_inicial = carrito_base.y
        carrito_base.moverse_y(Direccion.ABAJO)
        assert carrito_base.y > y_inicial

    def test_limite_superior_respetado(self, carrito_base):
        """No debe subir por encima del límite."""
        carrito_base.y = carrito_base.y_limite_superior + 1
        carrito_base.moverse_y(Direccion.ARRIBA)
        assert carrito_base.y >= carrito_base.y_limite_superior

    def test_limite_inferior_respetado(self, carrito_base):
        """No debe bajar por debajo del límite."""
        carrito_base.y = carrito_base.y_limite_inferior - 1
        carrito_base.moverse_y(Direccion.ABAJO)
        assert carrito_base.y <= carrito_base.y_limite_inferior

# TESTS: Carrito — salto
class TestCarritoSalto:

    def test_salto_inicia_correctamente(self, carrito_base):
        resultado = carrito_base.saltar()
        assert resultado is True
        assert carrito_base.saltando is True

    def test_color_cambia_al_saltar(self, carrito_base):
        carrito_base.saltar()
        assert carrito_base.color_actual == carrito_base.color_salto

    def test_no_doble_salto(self, carrito_base):
        carrito_base.saltar()
        segundo = carrito_base.saltar()
        assert segundo is False

    def test_carrito_sube_durante_salto(self, carrito_base):
        y_inicial = carrito_base.y
        carrito_base.saltar()
        carrito_base.actualizar(dt=1.0)   # primer tick: velocidad negativa domina
        assert carrito_base.y < y_inicial

    def test_aterrizaje_restaura_color(self, carrito_base):
        carrito_base.saltar()
        # Simular muchos ticks hasta que aterrice
        for _ in range(50):
            carrito_base.actualizar(dt=1.0)
            if not carrito_base.saltando:
                break
        assert carrito_base.saltando is False
        assert carrito_base.color_actual == carrito_base.color_base

    def test_aterrizaje_en_y_suelo(self, carrito_base):
        carrito_base.saltar()
        for _ in range(50):
            carrito_base.actualizar(dt=1.0)
            if not carrito_base.saltando:
                break
        assert carrito_base.y == pytest.approx(carrito_base.y_suelo)

    def test_velocidad_salto_negativa_al_inicio(self, carrito_base):
        """Al saltar, la velocidad vertical debe ser negativa (hacia arriba)."""
        carrito_base.saltar()
        assert carrito_base._vel_salto_actual < 0

# TESTS: Carrito — energía
class TestCarritoEnergia:

    def test_energia_inicial(self, carrito_base):
        assert carrito_base.energia == 100

    def test_recibir_danio(self, carrito_base):
        carrito_base.recibir_danio(20)
        assert carrito_base.energia == 80

    def test_energia_no_negativa(self, carrito_base):
        carrito_base.recibir_danio(9999)
        assert carrito_base.energia == 0

    def test_esta_vivo_con_energia(self, carrito_base):
        assert carrito_base.esta_vivo() is True

    def test_esta_vivo_sin_energia(self, carrito_base):
        carrito_base.recibir_danio(100)
        assert carrito_base.esta_vivo() is False

    def test_porcentaje_energia_lleno(self, carrito_base):
        assert carrito_base.porcentaje_energia() == pytest.approx(1.0)

    def test_porcentaje_energia_mitad(self, carrito_base):
        carrito_base.recibir_danio(50)
        assert carrito_base.porcentaje_energia() == pytest.approx(0.5)

    def test_porcentaje_energia_vacio(self, carrito_base):
        carrito_base.recibir_danio(100)
        assert carrito_base.porcentaje_energia() == pytest.approx(0.0)

# TESTS: Carrito — colisiones AABB
class TestCarritoColisiones:

    def test_colision_directa(self, carrito_base):
        """Obstáculo centrado en la misma posición que el carrito → colisión."""
        # Carrito en x=0 metro, y=360px. En pantalla x_px=0*10=0
        # Obstáculo: x1=-50, y1=340, x2=50, y2=380 → cubre la posición del carrito
        assert carrito_base.colisiona_con(-50, 340, 50, 380, camara_x=0, pixels_por_metro=10)

    def test_sin_colision_a_la_derecha(self, carrito_base):
        assert not carrito_base.colisiona_con(200, 340, 300, 380, camara_x=0, pixels_por_metro=10)

    def test_sin_colision_arriba(self, carrito_base):
        # Obstáculo muy arriba en pantalla
        assert not carrito_base.colisiona_con(-50, 0, 50, 100, camara_x=0, pixels_por_metro=10)

    def test_sin_colision_abajo(self, carrito_base):
        # Obstáculo muy abajo en pantalla
        assert not carrito_base.colisiona_con(-50, 600, 50, 700, camara_x=0, pixels_por_metro=10)

    def test_bbox_devuelve_cuatro_valores(self, carrito_base):
        bb = carrito_base.bbox()
        assert len(bb) == 4

    def test_bbox_x_izq_menor_x_der(self, carrito_base):
        x1, y1, x2, y2 = carrito_base.bbox()
        assert x1 < x2

    def test_bbox_y_top_menor_y_bot(self, carrito_base):
        x1, y1, x2, y2 = carrito_base.bbox()
        assert y1 < y2

# TESTS: FrameState
class TestFrameState:

    def _frame(self, carrito: Carrito) -> FrameState:
        return FrameState(
            carrito=carrito,
            obstaculos_visibles=[],
            estado_juego=GameState.JUGANDO,
            camara_x=0.0,
            distancia_total_m=1000,
        )

    def test_construccion_basica(self, carrito_base):
        fs = self._frame(carrito_base)
        assert fs.estado_juego == GameState.JUGANDO

    def test_distancia_recorrida(self, carrito_base):
        carrito_base.x = 250.0
        fs = self._frame(carrito_base)
        assert fs.distancia_recorrida_m() == pytest.approx(250.0)

    def test_porcentaje_progreso(self, carrito_base):
        carrito_base.x = 500.0
        fs = self._frame(carrito_base)
        assert fs.porcentaje_progreso() == pytest.approx(0.5)

    def test_porcentaje_no_supera_1(self, carrito_base):
        carrito_base.x = 9999.0
        fs = self._frame(carrito_base)
        assert fs.porcentaje_progreso() <= 1.0

    def test_esta_en_meta(self, carrito_base):
        carrito_base.x = 1000.0
        fs = self._frame(carrito_base)
        assert fs.esta_en_meta() is True

    def test_no_esta_en_meta(self, carrito_base):
        carrito_base.x = 500.0
        fs = self._frame(carrito_base)
        assert fs.esta_en_meta() is False

    def test_repr(self, carrito_base):
        fs = self._frame(carrito_base)
        assert "FrameState" in repr(fs)

# TESTS: Integración JSON -> AVL -> rango()
class TestIntegracionJSONAVL:

    def test_obstaculos_del_json_se_insertan_en_avl(self, config_valido):
        arbol = ArbolAVL()
        for obs in config_valido.obstaculos():
            arbol.insertar(obs)
        assert arbol.total_nodos == 3

    def test_rango_retorna_obstaculos_visibles(self, config_valido):
        arbol = ArbolAVL()
        for obs in config_valido.obstaculos():
            arbol.insertar(obs)
        # Ventana visible: x=[0, 300], y=[0, 720]
        visibles = arbol.rango(0, 300, 0, 720)
        # ROCA en x=100 y BARRIL en x=250 deben estar
        tipos_visibles = {o.tipo for o in visibles}
        assert TipoObstaculo.ROCA   in tipos_visibles
        assert TipoObstaculo.BARRIL in tipos_visibles

    def test_obstaculo_fuera_de_ventana_no_aparece(self, config_valido):
        arbol = ArbolAVL()
        for obs in config_valido.obstaculos():
            arbol.insertar(obs)
        # Ventana estrecha: solo x=[320, 500]
        visibles = arbol.rango(320, 500, 0, 720)
        # CHARCO en x=350 debe aparecer; ROCA y BARRIL no
        tipos = {o.tipo for o in visibles}
        assert TipoObstaculo.CHARCO in tipos
        assert TipoObstaculo.ROCA   not in tipos
        assert TipoObstaculo.BARRIL not in tipos

    def test_arbol_balanceado_con_obstaculos_del_json(self, config_valido):
        arbol = ArbolAVL()
        for obs in config_valido.obstaculos():
            arbol.insertar(obs)
        # Verificar balance de todos los nodos
        def verificar(nodo):
            if nodo is None:
                return
            assert abs(nodo.factor_balance) <= 1
            verificar(nodo.izquierdo)
            verificar(nodo.derecho)
        verificar(arbol.raiz)

    def test_inorden_con_obstaculos_del_json(self, config_valido):
        arbol = ArbolAVL()
        for obs in config_valido.obstaculos():
            arbol.insertar(obs)
        lista = arbol.inorden()
        claves = [o.clave_avl() for o in lista]
        assert claves == sorted(claves)

    def test_bfs_niveles_con_obstaculos_del_json(self, config_valido):
        arbol = ArbolAVL()
        for obs in config_valido.obstaculos():
            arbol.insertar(obs)
        niveles = arbol.bfs()
        total = sum(len(nivel) for nivel in niveles)
        assert total == arbol.total_nodos

    def test_flujo_completo_velocidades_del_json(self, config_valido):
        """Simula la carga completa: JSON -> Carrito -> 5 ticks -> posición correcta."""
        vel_x   = config_valido.get_juego("velocidad_x_ms")
        vel_y   = config_valido.get_juego("velocidad_y_ms")
        energia = config_valido.get_juego("energia_inicial")
        color_b = config_valido.color_carrito()
        color_s = config_valido.color_salto()

        carrito = Carrito(
            x=0.0, y=360.0, y_suelo=360.0,
            velocidad_x=vel_x, velocidad_y=vel_y,
            energia=energia, energia_maxima=energia,
            color_base=color_b, color_salto=color_s,
        )
        for _ in range(5):
            carrito.actualizar(dt=1.0)

        assert carrito.x == pytest.approx(vel_x * 5)
        assert carrito.esta_vivo() is True

    def test_sin_pygame_en_fase2(self):
        """Verificar que ningún módulo de Fase 2 importa Pygame."""
        assert "pygame" not in sys.modules, (
            "Pygame no debe estar importado en Fase 2. "
            "La lógica debe ser completamente independiente del motor gráfico."
        )