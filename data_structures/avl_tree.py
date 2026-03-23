"""
Árbol AVL completo. Sin dependencia de Pygame ni de ninguna capa superior.

Operaciones implementadas:
    - insertar(obstaculo)         → bool
    - eliminar(x1, y1)            → bool
    - buscar(x1, y1)              → Obstaculo | None
    - rango(xmin, xmax, ymin, ymax) → list[Obstaculo]
    - inorden()                   → list[Obstaculo]
    - preorden()                  → list[Obstaculo]
    - postorden()                 → list[Obstaculo]
    - bfs()                       → list[list[NodoAVL]]

Regla de comparación:
    Primero se compara x1. En caso de empate, se compara y1.
    Coordenadas duplicadas (x1 == x2 AND y1 == y2) son rechazadas.
"""
from __future__ import annotations
from collections import deque
from models.obstaculo import Obstaculo
from data_structures.avl_node import NodoAVL

class ArbolAVL:
    """Árbol AVL de obstáculos, ordenado por (x1, y1)."""

    def __init__(self) -> None:
        self.raiz:        NodoAVL | None = None
        self.total_nodos: int            = 0

    # Propiedades públicas
    @property
    def altura(self) -> int:
        """Altura del árbol. 0 si está vacío."""
        return self.raiz.altura if self.raiz else 0

    def esta_vacio(self) -> bool:
        return self.raiz is None

    # Inserción
    def insertar(self, obstaculo: Obstaculo) -> bool:
        """
        Inserta un obstáculo en el árbol.
        Retorna True si fue insertado, False si la clave ya existía.
        """
        nueva_raiz, insertado = self._insertar(self.raiz, obstaculo)
        self.raiz = nueva_raiz
        if insertado:
            self.total_nodos += 1
        return insertado

    def _insertar(
        self, nodo: NodoAVL | None, obstaculo: Obstaculo
    ) -> tuple[NodoAVL, bool]:
        """Recursión interna. Retorna (nodo_actualizado, fue_insertado)."""

        # Caso base: posición vacía → crear hoja
        if nodo is None:
            return NodoAVL(obstaculo), True

        clave_nueva = obstaculo.clave_avl()
        clave_nodo  = nodo.clave()

        if clave_nueva < clave_nodo:
            nodo.izquierdo, insertado = self._insertar(nodo.izquierdo, obstaculo)
        elif clave_nueva > clave_nodo:
            nodo.derecho,   insertado = self._insertar(nodo.derecho,   obstaculo)
        else:
            # Clave duplicada → rechazar sin modificar el árbol
            return nodo, False

        # Actualizar altura y balancear en el camino de vuelta
        nodo.actualizar_altura()
        return self._balancear(nodo), insertado

    # Eliminar
    def eliminar(self, x1: int, y1: int) -> bool:
        """
        Elimina el nodo con clave (x1, y1).
        Retorna True si existía y fue eliminado, False si no existía.
        """
        nueva_raiz, eliminado = self._eliminar(self.raiz, (x1, y1))
        self.raiz = nueva_raiz
        if eliminado:
            self.total_nodos -= 1
        return eliminado

    def _eliminar(
        self, nodo: NodoAVL | None, clave: tuple[int, int]
    ) -> tuple[NodoAVL | None, bool]:
        """Recursión interna. Retorna (nodo_actualizado, fue_eliminado)."""

        if nodo is None:
            return None, False

        clave_nodo = nodo.clave()

        if clave < clave_nodo:
            nodo.izquierdo, eliminado = self._eliminar(nodo.izquierdo, clave)
        elif clave > clave_nodo:
            nodo.derecho,   eliminado = self._eliminar(nodo.derecho,   clave)
        else:
            # Nodo encontrado — tres casos:
            eliminado = True

            # Caso 1/2: cero o un hijo
            if nodo.izquierdo is None:
                return nodo.derecho, eliminado
            if nodo.derecho is None:
                return nodo.izquierdo, eliminado

            # Caso 3: dos hijos -> sucesor inorden (mínimo del subárbol derecho)
            sucesor           = self._minimo(nodo.derecho)
            nodo.obstaculo    = sucesor.obstaculo
            nodo.derecho, _   = self._eliminar(nodo.derecho, sucesor.clave())

        nodo.actualizar_altura()
        return self._balancear(nodo), eliminado

    @staticmethod
    def _minimo(nodo: NodoAVL) -> NodoAVL:
        """Retorna el nodo con la clave mínima en el subárbol."""
        actual = nodo
        while actual.izquierdo is not None:
            actual = actual.izquierdo
        return actual

    # Búsqueda Exacta
    def buscar(self, x1: int, y1: int) -> Obstaculo | None:
        """Busca el obstáculo con clave (x1, y1). O(log N)."""
        nodo = self._buscar_nodo(self.raiz, (x1, y1))
        return nodo.obstaculo if nodo else None

    def _buscar_nodo(
        self, nodo: NodoAVL | None, clave: tuple[int, int]
    ) -> NodoAVL | None:
        if nodo is None:
            return None
        clave_nodo = nodo.clave()
        if clave == clave_nodo:
            return nodo
        if clave < clave_nodo:
            return self._buscar_nodo(nodo.izquierdo, clave)
        return self._buscar_nodo(nodo.derecho, clave)

    # Búsqueda por Rango <- Operación crítica
    def rango(
        self,
        xmin: int | float,
        xmax: int | float,
        ymin: int | float,
        ymax: int | float,
    ) -> list[Obstaculo]:
        """
        Devuelve todos los obstáculos cuya clave (x1, y1) esté dentro
        del rectángulo [xmin, xmax] × [ymin, ymax].

        Complejidad: O(log N + K) donde K = cantidad de resultados.

        La poda funciona así:
            - Si x_nodo < xmin → nada en su subárbol izquierdo puede coincidir
            (todos tienen x ≤ x_nodo < xmin), pero sí puede el derecho.
            - Si x_nodo > xmax → nada en su subárbol derecho puede coincidir,
            pero sí puede el izquierdo.
            - Si xmin ≤ x_nodo ≤ xmax → revisar ambos subárboles y el nodo mismo.
        """
        resultado: list[Obstaculo] = []
        self._rango(self.raiz, xmin, xmax, ymin, ymax, resultado)
        return resultado

    def _rango(
        self,
        nodo: NodoAVL | None,
        xmin: int | float,
        xmax: int | float,
        ymin: int | float,
        ymax: int | float,
        resultado: list[Obstaculo],
    ) -> None:
        if nodo is None:
            return
        x_nodo, y_nodo = nodo.clave()

        # Subárbol izquierdo: solo si puede haber x >= xmin
        if x_nodo >= xmin:
            self._rango(nodo.izquierdo, xmin, xmax, ymin, ymax, resultado)

        # ¿Este nodo está dentro del rango?
        if xmin <= x_nodo <= xmax and ymin <= y_nodo <= ymax:
            if not nodo.obstaculo.eliminado:
                resultado.append(nodo.obstaculo)

        # Subárbol derecho: solo si puede haber x <= xmax
        if x_nodo <= xmax:
            self._rango(nodo.derecho, xmin, xmax, ymin, ymax, resultado)

    # Recorridos en Profundidad
    def inorden(self) -> list[Obstaculo]:
        """Izq → Raíz → Der. Devuelve obstáculos ordenados por (x1, y1)."""
        return self._inorden_nodo(self.raiz)

    def _inorden_nodo(self, nodo: NodoAVL | None) -> list[Obstaculo]:
        if nodo is None:
            return []
        return [
            *self._inorden_nodo(nodo.izquierdo),
            nodo.obstaculo,
            *self._inorden_nodo(nodo.derecho),
        ]

    def preorden(self) -> list[Obstaculo]:
        """Raíz → Izq → Der. Útil para serializar la estructura."""
        return self._preorden_nodo(self.raiz)

    def _preorden_nodo(self, nodo: NodoAVL | None) -> list[Obstaculo]:
        if nodo is None:
            return []
        return [
            nodo.obstaculo,
            *self._preorden_nodo(nodo.izquierdo),
            *self._preorden_nodo(nodo.derecho),
        ]

    def postorden(self) -> list[Obstaculo]:
        """Izq → Der → Raíz. Útil para liberar/eliminar nodos de forma segura."""
        return self._postorden_nodo(self.raiz)

    def _postorden_nodo(self, nodo: NodoAVL | None) -> list[Obstaculo]:
        if nodo is None:
            return []
        return [
            *self._postorden_nodo(nodo.izquierdo),
            *self._postorden_nodo(nodo.derecho),
            nodo.obstaculo,
        ]

    # Recorridos en Anchura
    def bfs(self) -> list[list[NodoAVL]]:
        """
        Recorrido por niveles. Retorna lista de listas de NodoAVL.
        Cada sublista corresponde a un nivel del árbol.
        Usado por AVLVisualizer para dibujar el árbol nivel por nivel.
        """
        if self.raiz is None:
            return []

        niveles: list[list[NodoAVL]] = []
        cola: deque[NodoAVL] = deque([self.raiz])   # cola FIFO, O(1) popleft

        while cola:
            nivel_actual: list[NodoAVL] = []
            for _ in range(len(cola)):               # len(cola) = nodos de este nivel
                nodo = cola.popleft()                # FIFO: primero en entrar, primero en salir
                nivel_actual.append(nodo)
                if nodo.izquierdo:
                    cola.append(nodo.izquierdo)
                if nodo.derecho:
                    cola.append(nodo.derecho)
            niveles.append(nivel_actual)

        return niveles

    def bfs_lista(self) -> list[Obstaculo]:
        """BFS plano: devuelve todos los obstáculos nivel por nivel (lista simple)."""
        return [nodo.obstaculo for nivel in self.bfs() for nodo in nivel]

    # Rotaciones AVL
    def _rotar_derecha(self, z: NodoAVL) -> NodoAVL:
        """
        Rotacion simple a la derecha (casos LL).
 
              z                y
             /|              / |
            y   T4    ->   x   z
           /|                 /|
          x   T3             T3 T4
        """
        y  = z.izquierdo
        T3 = y.derecho
        y.derecho   = z
        z.izquierdo = T3
        z.actualizar_altura()   # z primero (ahora es hijo)
        y.actualizar_altura()   # y después (nueva raíz)
        return y

    def _rotar_izquierda(self, z: NodoAVL) -> NodoAVL:
        """
        Rotacion simple a la izquierda (casos RR).
 
          z                  y
         /|                 /|
        T1   y      ->     z   x
            /|            /|
           T2   x        T1  T2
        """
        y  = z.derecho
        T2 = y.izquierdo
        y.izquierdo = z
        z.derecho   = T2
        z.actualizar_altura()
        y.actualizar_altura()
        return y

    # Balanceo
    def _balancear(self, nodo: NodoAVL) -> NodoAVL:
        """
        Aplica la rotación necesaria si el nodo está desbalanceado.
        Retorna la nueva raíz del subárbol.

        Los cuatro casos:
            LL: fb(nodo)=+2, fb(hijo_izq)>=0   → rotar_derecha(nodo)
            LR: fb(nodo)=+2, fb(hijo_izq)<0    → rotar_izq(hijo) + rotar_der(nodo)
            RR: fb(nodo)=-2, fb(hijo_der)<=0   → rotar_izquierda(nodo)
            RL: fb(nodo)=-2, fb(hijo_der)>0    → rotar_der(hijo) + rotar_izq(nodo)
        """
        fb = nodo.factor_balance

        # Caso LL
        if fb > 1 and nodo.izquierdo and nodo.izquierdo.factor_balance >= 0:
            return self._rotar_derecha(nodo)

        # Caso LR
        if fb > 1 and nodo.izquierdo and nodo.izquierdo.factor_balance < 0:
            nodo.izquierdo = self._rotar_izquierda(nodo.izquierdo)
            return self._rotar_derecha(nodo)

        # Caso RR
        if fb < -1 and nodo.derecho and nodo.derecho.factor_balance <= 0:
            return self._rotar_izquierda(nodo)

        # Caso RL
        if fb < -1 and nodo.derecho and nodo.derecho.factor_balance > 0:
            nodo.derecho = self._rotar_derecha(nodo.derecho)
            return self._rotar_izquierda(nodo)

        return nodo  # ya estaba balanceado

    # Utilidades
    def __len__(self) -> int:
        return self.total_nodos

    def __repr__(self) -> str:
        return f"ArbolAVL(nodos={self.total_nodos}, altura={self.altura})"

    def imprimir_estructura(self) -> None:
        """Imprime el árbol en consola (útil para debug y Fase 3)."""
        self._imprimir_nodo(self.raiz, prefijo="", es_izquierdo=True, es_raiz=True)

    def _imprimir_nodo(
        self,
        nodo: NodoAVL | None,
        prefijo: str,
        es_izquierdo: bool,
        es_raiz: bool = False,
    ) -> None:
        if nodo is None:
            return
        conector      = "" if es_raiz else ("+-IZQ- " if es_izquierdo else "+-DER- ")
        extension     = "" if es_raiz else ("|      " if es_izquierdo else "       ")
        x, y          = nodo.clave()
        print(
            f"{prefijo}{conector}"
            f"({x},{y}) [{nodo.obstaculo.tipo.value}] "
            f"h={nodo.altura} fb={nodo.factor_balance}"
        )
        nuevo_prefijo = prefijo + extension
        if nodo.izquierdo or nodo.derecho:
            self._imprimir_nodo(nodo.izquierdo, nuevo_prefijo, True)
            self._imprimir_nodo(nodo.derecho,   nuevo_prefijo, False)