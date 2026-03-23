"""
Suite completa de pruebas para la Fase 1.
Cubre: NodoAVL, ArbolAVL (inserción, rotaciones, eliminación,
       búsqueda exacta, búsqueda por rango, los 4 recorridos).

Ejecutar: pytest tests/test_avl.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.obstaculo import Obstaculo
from data_structures.avl_node import NodoAVL
from data_structures.avl_tree import ArbolAVL
from core.enums import TipoObstaculo

# HELPERS
def obs(x1: int, y1: int, tipo: TipoObstaculo = TipoObstaculo.ROCA, danio: int = 10) -> Obstaculo:
    """Crea un Obstaculo mínimo para tests."""
    return Obstaculo(x1=x1, y1=y1, x2=x1 + 40, y2=y1 + 40, tipo=tipo, danio=danio)


def arbol_con(*claves: tuple[int, int]) -> ArbolAVL:
    """Crea un ArbolAVL con los obstáculos dados por sus claves (x1, y1)."""
    a = ArbolAVL()
    for x, y in claves:
        a.insertar(obs(x, y))
    return a

# TESTS: Obstaculo
class TestObstaculo:

    def test_clave_avl_correcta(self):
        o = obs(100, 200)
        assert o.clave_avl() == (100, 200)

    def test_bbox_correcta(self):
        o = obs(50, 80)
        assert o.bbox() == (50, 80, 90, 120)

    def test_coordenadas_invalidas_x(self):
        with pytest.raises(ValueError):
            Obstaculo(x1=100, y1=0, x2=50, y2=50, tipo=TipoObstaculo.ROCA, danio=10)

    def test_coordenadas_invalidas_y(self):
        with pytest.raises(ValueError):
            Obstaculo(x1=0, y1=100, x2=50, y2=50, tipo=TipoObstaculo.ROCA, danio=10)

    def test_danio_negativo_invalido(self):
        with pytest.raises(ValueError):
            Obstaculo(x1=0, y1=0, x2=10, y2=10, tipo=TipoObstaculo.ROCA, danio=-5)

    def test_color_segun_tipo(self):
        o = obs(0, 0, TipoObstaculo.BARRIL)
        color = o.color()
        assert isinstance(color, tuple) and len(color) == 3

# TESTS: NodoAVL
class TestNodoAVL:

    def test_clave_correcta(self):
        n = NodoAVL(obs(10, 20))
        assert n.clave() == (10, 20)

    def test_altura_inicial_uno(self):
        n = NodoAVL(obs(0, 0))
        assert n.altura == 1

    def test_factor_balance_hoja_es_cero(self):
        n = NodoAVL(obs(0, 0))
        assert n.factor_balance == 0

    def test_actualizar_altura_con_hijos(self):
        raiz = NodoAVL(obs(10, 0))
        raiz.izquierdo = NodoAVL(obs(5, 0))
        raiz.actualizar_altura()
        assert raiz.altura == 2

    def test_factor_balance_con_hijo_izquierdo(self):
        raiz = NodoAVL(obs(10, 0))
        raiz.izquierdo = NodoAVL(obs(5, 0))
        raiz.actualizar_altura()
        assert raiz.factor_balance == 1

# TESTS: Inserción básica
class TestInsercion:

    def test_insertar_en_arbol_vacio(self):
        a = ArbolAVL()
        assert a.insertar(obs(10, 10)) is True
        assert a.total_nodos == 1

    def test_insertar_duplicado_retorna_false(self):
        a = ArbolAVL()
        a.insertar(obs(10, 10))
        assert a.insertar(obs(10, 10)) is False
        assert a.total_nodos == 1

    def test_insertar_mismo_x_diferente_y(self):
        """Mismo x1 pero diferente y1 → debe aceptarse."""
        a = ArbolAVL()
        assert a.insertar(obs(10, 10)) is True
        assert a.insertar(obs(10, 20)) is True
        assert a.total_nodos == 2

    def test_insertar_orden_creciente(self):
        a = arbol_con((10, 0), (20, 0), (30, 0), (40, 0), (50, 0))
        assert a.total_nodos == 5
        # El AVL debe mantener el árbol balanceado (altura ≤ ceil(1.44 * log2(n+2)))
        assert a.altura <= 4

    def test_insertar_orden_decreciente(self):
        a = arbol_con((50, 0), (40, 0), (30, 0), (20, 0), (10, 0))
        assert a.total_nodos == 5
        assert a.altura <= 4

    def test_arbol_balanceado_tras_muchas_inserciones(self):
        import math
        n = 31
        a = ArbolAVL()
        for i in range(n):
            a.insertar(obs(i * 10, 0))
        max_altura = int(math.ceil(1.45 * math.log2(n + 2)))
        assert a.altura <= max_altura

# TESTS: Rotaciones explícitas
class TestRotaciones:

    def test_rotacion_ll(self):
        """Insertar 30, 20, 10 → rotación LL → raíz debe ser 20."""
        a = arbol_con((30, 0), (20, 0), (10, 0))
        assert a.raiz.clave() == (20, 0)
        assert a.raiz.izquierdo.clave() == (10, 0)
        assert a.raiz.derecho.clave()   == (30, 0)

    def test_rotacion_rr(self):
        """Insertar 10, 20, 30 → rotación RR → raíz debe ser 20."""
        a = arbol_con((10, 0), (20, 0), (30, 0))
        assert a.raiz.clave() == (20, 0)
        assert a.raiz.izquierdo.clave() == (10, 0)
        assert a.raiz.derecho.clave()   == (30, 0)

    def test_rotacion_lr(self):
        """Insertar 30, 10, 20 → rotación LR → raíz debe ser 20."""
        a = arbol_con((30, 0), (10, 0), (20, 0))
        assert a.raiz.clave() == (20, 0)
        assert a.raiz.izquierdo.clave() == (10, 0)
        assert a.raiz.derecho.clave()   == (30, 0)

    def test_rotacion_rl(self):
        """Insertar 10, 30, 20 → rotación RL → raíz debe ser 20."""
        a = arbol_con((10, 0), (30, 0), (20, 0))
        assert a.raiz.clave() == (20, 0)
        assert a.raiz.izquierdo.clave() == (10, 0)
        assert a.raiz.derecho.clave()   == (30, 0)

    def test_factor_balance_siempre_valido(self):
        """Ningún nodo debe tener |factor_balance| > 1."""
        a = arbol_con(
            (50, 0), (30, 0), (70, 0), (20, 0), (40, 0),
            (60, 0), (80, 0), (10, 0), (25, 0),
        )
        self._verificar_balance(a.raiz)

    def _verificar_balance(self, nodo: NodoAVL | None) -> None:
        if nodo is None:
            return
        assert abs(nodo.factor_balance) <= 1, (
            f"Nodo {nodo.clave()} tiene factor_balance={nodo.factor_balance}"
        )
        self._verificar_balance(nodo.izquierdo)
        self._verificar_balance(nodo.derecho)

# TESTS: Búsqueda exacta
class TestBusqueda:

    def test_buscar_existente(self):
        a = arbol_con((10, 0), (20, 0), (30, 0))
        resultado = a.buscar(20, 0)
        assert resultado is not None
        assert resultado.clave_avl() == (20, 0)

    def test_buscar_inexistente_retorna_none(self):
        a = arbol_con((10, 0), (20, 0))
        assert a.buscar(99, 0) is None

    def test_buscar_en_arbol_vacio(self):
        a = ArbolAVL()
        assert a.buscar(0, 0) is None

    def test_buscar_por_y_diferente(self):
        """Mismo x, diferente y → claves distintas."""
        a = arbol_con((10, 0), (10, 100))
        assert a.buscar(10, 0)   is not None
        assert a.buscar(10, 100) is not None
        assert a.buscar(10, 50)  is None

# TESTS: Eliminación
class TestEliminacion:

    def test_eliminar_hoja(self):
        a = arbol_con((10, 0), (20, 0), (30, 0))
        assert a.eliminar(10, 0) is True
        assert a.total_nodos == 2
        assert a.buscar(10, 0) is None

    def test_eliminar_con_un_hijo(self):
        a = arbol_con((20, 0), (10, 0), (30, 0), (5, 0))
        assert a.eliminar(10, 0) is True
        assert a.buscar(10, 0) is None
        assert a.buscar(5, 0)  is not None

    def test_eliminar_con_dos_hijos(self):
        a = arbol_con((20, 0), (10, 0), (30, 0))
        assert a.eliminar(20, 0) is True
        assert a.total_nodos == 2
        assert a.buscar(10, 0) is not None
        assert a.buscar(30, 0) is not None

    def test_eliminar_raiz_unica(self):
        a = arbol_con((10, 0),)
        assert a.eliminar(10, 0) is True
        assert a.esta_vacio()

    def test_eliminar_inexistente_retorna_false(self):
        a = arbol_con((10, 0), (20, 0))
        assert a.eliminar(99, 0) is False
        assert a.total_nodos == 2

    def test_balance_tras_eliminacion(self):
        """El árbol debe seguir balanceado después de múltiples eliminaciones."""
        claves = [(i * 10, 0) for i in range(1, 16)]
        a = arbol_con(*claves)
        for i in range(1, 8):
            a.eliminar(i * 10, 0)
        self._verificar_balance(a.raiz)

    def _verificar_balance(self, nodo: NodoAVL | None) -> None:
        if nodo is None:
            return
        assert abs(nodo.factor_balance) <= 1
        self._verificar_balance(nodo.izquierdo)
        self._verificar_balance(nodo.derecho)

# TESTS: Búsqueda por rango
class TestRango:

    def _arbol_juego(self) -> ArbolAVL:
        """
        Árbol de prueba representando obstáculos en distintas posiciones.
        x1: distancia en metros. y1: altura en píxeles.
        """
        a = ArbolAVL()
        datos = [
            (100, 300), (200, 150), (300, 400), (400, 300),
            (500, 200), (600, 350), (700, 100), (800, 300),
            (50, 200),  (900, 400),
        ]
        for x, y in datos:
            a.insertar(obs(x, y))
        return a

    def test_rango_completo(self):
        a = self._arbol_juego()
        resultado = a.rango(0, 1000, 0, 500)
        assert len(resultado) == 10

    def test_rango_vacio(self):
        a = self._arbol_juego()
        resultado = a.rango(1100, 1200, 0, 500)
        assert resultado == []

    def test_rango_ventana_visible(self):
        """Simula la ventana visible del juego: x=[200,500], y=[0,500]."""
        a = self._arbol_juego()
        resultado = a.rango(200, 500, 0, 500)
        claves = {o.clave_avl() for o in resultado}
        assert (200, 150) in claves
        assert (300, 400) in claves
        assert (400, 300) in claves
        assert (500, 200) in claves
        # Fuera del rango:
        assert (100, 300) not in claves
        assert (600, 350) not in claves

    def test_rango_por_y_excluye_carril(self):
        """Filtra por carril Y: solo obstáculos en carril medio."""
        a = self._arbol_juego()
        resultado = a.rango(0, 1000, 250, 399)
        for o in resultado:
            assert 250 <= o.y1 <= 399

    def test_rango_excluye_eliminados(self):
        """Obstáculos marcados como eliminado=True no deben aparecer."""
        a = self._arbol_juego()
        o_buscar = a.buscar(100, 300)
        assert o_buscar is not None
        o_buscar.eliminado = True

        resultado = a.rango(0, 200, 0, 500)
        for o in resultado:
            assert not o.eliminado

    def test_rango_exacto_en_borde(self):
        """La clave exactamente en el borde del rango debe incluirse."""
        a = arbol_con((100, 0), (200, 0), (300, 0))
        resultado = a.rango(100, 200, 0, 50)
        claves = [o.clave_avl() for o in resultado]
        assert (100, 0) in claves
        assert (200, 0) in claves
        assert (300, 0) not in claves

    def test_rango_sin_pygame(self):
        """Verificar que rango() funciona sin importar pygame."""
        import sys
        assert "pygame" not in sys.modules, "pygame no debe estar importado en Fase 1"
        a = arbol_con((10, 0), (20, 0))
        resultado = a.rango(0, 100, 0, 100)
        assert len(resultado) == 2

# TESTS: Recorridos en profundidad
class TestRecorridos:

    def _arbol_5nodos(self) -> ArbolAVL:
        """Árbol balanceado con 5 nodos: claves 10,20,30,40,50."""
        return arbol_con((10, 0), (20, 0), (30, 0), (40, 0), (50, 0))

    def test_inorden_ordenado(self):
        """Inorden debe devolver los obstáculos en orden creciente de clave."""
        a = self._arbol_5nodos()
        resultado = a.inorden()
        claves = [o.clave_avl() for o in resultado]
        assert claves == sorted(claves), f"Inorden no está ordenado: {claves}"

    def test_inorden_tamanio(self):
        a = self._arbol_5nodos()
        assert len(a.inorden()) == 5

    def test_preorden_raiz_primero(self):
        """Preorden debe incluir la raíz como primer elemento."""
        a = self._arbol_5nodos()
        resultado = a.preorden()
        assert resultado[0].clave_avl() == a.raiz.clave()

    def test_postorden_raiz_ultimo(self):
        """Postorden debe incluir la raíz como último elemento."""
        a = self._arbol_5nodos()
        resultado = a.postorden()
        assert resultado[-1].clave_avl() == a.raiz.clave()

    def test_todos_los_recorridos_contienen_mismos_elementos(self):
        a = self._arbol_5nodos()
        set_in   = {o.clave_avl() for o in a.inorden()}
        set_pre  = {o.clave_avl() for o in a.preorden()}
        set_post = {o.clave_avl() for o in a.postorden()}
        assert set_in == set_pre == set_post

    def test_recorridos_arbol_vacio(self):
        a = ArbolAVL()
        assert a.inorden()   == []
        assert a.preorden()  == []
        assert a.postorden() == []

    def test_recorrido_nodo_unico(self):
        a = arbol_con((42, 7),)
        assert len(a.inorden())   == 1
        assert len(a.preorden())  == 1
        assert len(a.postorden()) == 1

# TESTS: BFS (anchura)
class TestBFS:

    def test_bfs_arbol_vacio(self):
        a = ArbolAVL()
        assert a.bfs() == []

    def test_bfs_un_nodo(self):
        a = arbol_con((10, 0),)
        niveles = a.bfs()
        assert len(niveles) == 1
        assert len(niveles[0]) == 1

    def test_bfs_tres_nodos_dos_niveles(self):
        """
        Árbol:      20
                   /  \
                  10   30
        """
        a = arbol_con((20, 0), (10, 0), (30, 0))
        niveles = a.bfs()
        assert len(niveles) == 2
        assert len(niveles[0]) == 1   # raíz
        assert len(niveles[1]) == 2   # hojas

    def test_bfs_nivel_0_es_raiz(self):
        a = arbol_con((30, 0), (20, 0), (10, 0))
        niveles = a.bfs()
        assert niveles[0][0].clave() == a.raiz.clave()

    def test_bfs_total_nodos_correcto(self):
        a = arbol_con((10, 0), (20, 0), (30, 0), (40, 0), (50, 0))
        total = sum(len(nivel) for nivel in a.bfs())
        assert total == a.total_nodos

    def test_bfs_lista_plana(self):
        a = arbol_con((10, 0), (20, 0), (30, 0))
        lista = a.bfs_lista()
        assert len(lista) == 3
        assert all(isinstance(o, Obstaculo) for o in lista)

    def test_bfs_orden_niveles(self):
        """Cada nivel debe estar "más abajo" que el anterior."""
        a = arbol_con(
            (40, 0), (20, 0), (60, 0), (10, 0), (30, 0), (50, 0), (70, 0)
        )
        niveles = a.bfs()
        # El árbol perfecto de 7 nodos tiene 3 niveles
        assert len(niveles) == 3
        assert len(niveles[0]) == 1
        assert len(niveles[1]) == 2
        assert len(niveles[2]) == 4

# TESTS: Propiedades invariantes del AVL
class TestInvariantes:

    def _verificar_bst(self, nodo: NodoAVL | None) -> None:
        """Verifica que el árbol cumple la propiedad BST en cada nodo."""
        if nodo is None:
            return
        if nodo.izquierdo:
            assert nodo.izquierdo.clave() < nodo.clave(), (
                f"Violación BST: hijo_izq {nodo.izquierdo.clave()} >= {nodo.clave()}"
            )
        if nodo.derecho:
            assert nodo.derecho.clave() > nodo.clave(), (
                f"Violación BST: hijo_der {nodo.derecho.clave()} <= {nodo.clave()}"
            )
        self._verificar_bst(nodo.izquierdo)
        self._verificar_bst(nodo.derecho)

    def _verificar_avl(self, nodo: NodoAVL | None) -> None:
        """Verifica que todos los nodos cumplen |fb| ≤ 1."""
        if nodo is None:
            return
        assert abs(nodo.factor_balance) <= 1
        self._verificar_avl(nodo.izquierdo)
        self._verificar_avl(nodo.derecho)

    def _verificar_alturas(self, nodo: NodoAVL | None) -> int:
        """Verifica que la altura almacenada es correcta. Retorna la altura real."""
        if nodo is None:
            return 0
        h_izq = self._verificar_alturas(nodo.izquierdo)
        h_der = self._verificar_alturas(nodo.derecho)
        altura_esperada = 1 + max(h_izq, h_der)
        assert nodo.altura == altura_esperada, (
            f"Nodo {nodo.clave()}: altura={nodo.altura}, esperada={altura_esperada}"
        )
        return altura_esperada

    def test_invariantes_tras_inserciones_aleatorias(self):
        import random
        random.seed(42)
        claves = list({(random.randint(0, 500), random.randint(0, 500)) for _ in range(50)})
        a = arbol_con(*claves)
        self._verificar_bst(a.raiz)
        self._verificar_avl(a.raiz)
        self._verificar_alturas(a.raiz)

    def test_invariantes_tras_inserciones_y_eliminaciones(self):
        import random
        random.seed(7)
        claves = [(i * 13 % 200, i * 7 % 100) for i in range(30)]
        claves = list({c for c in claves})  # deduplicar
        a = arbol_con(*claves)

        # Eliminar la mitad aleatoriamente
        random.shuffle(claves)
        for x, y in claves[:len(claves)//2]:
            a.eliminar(x, y)

        self._verificar_bst(a.raiz)
        self._verificar_avl(a.raiz)
        self._verificar_alturas(a.raiz)

    def test_len_operador(self):
        a = arbol_con((1, 0), (2, 0), (3, 0))
        assert len(a) == 3

    def test_esta_vacio(self):
        a = ArbolAVL()
        assert a.esta_vacio() is True
        a.insertar(obs(1, 1))
        assert a.esta_vacio() is False