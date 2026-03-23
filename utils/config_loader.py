"""
Carga, valida e interpreta game_config.json.

Responsabilidades (según UML y diagrama de flujo):
    - Abrir y parsear el JSON.
    - Validar cada campo con reglas claras; lanzar errores DESCRIPTIVOS.
    - Exponer get(clave, default) para acceso genérico.
    - Exponer obstaculos() que retorna lista de Obstaculo listos para insertar en ArbolAVL.
    - Exponer hex_a_rgb() para convertir colores del JSON a tuplas (R,G,B).

Sin dependencia de Pygame ni de ArbolAVL: solo crea objetos Obstaculo.
El GameEngine es quien llama a arbol.insertar() en el loop de inicio.

Notas de diseño:
    - Se usa json estándar (no jsonschema) para mantener dependencias mínimas.
    - Las validaciones siguen el patrón "fail fast": se acumulan todos los errores
    encontrados y se lanzan juntos para que el desarrollador los corrija de una vez,
    en lugar de descubrir un error por ejecución.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.enums import TipoObstaculo
from models.obstaculo import Obstaculo

# Regex para validar colores hexadecimales #RRGGBB
_RE_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

class ConfigLoader:
    """
    Carga y valida game_config.json.

    Uso típico (desde GameEngine.__init__):
        config = ConfigLoader()
        config.cargar("config/game_config.json")
        for obs in config.obstaculos():
            arbol.insertar(obs)
    """

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._ruta: str = ""
        self._cargado: bool = False

    # Carga principal
    def cargar(self, ruta: str | Path) -> None:
        """
        Lee el JSON, valida su estructura completa y almacena la configuración.
        Lanza ConfigError con TODOS los errores encontrados de una sola vez.

        Secuencia del diagrama de flujo:
            Inicio -> Cargar ConfigLoader + JSON -> validar() -> continuar
        """
        ruta = Path(ruta)
        if not ruta.exists():
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: '{ruta}'\n"
                f"  Ruta absoluta buscada: {ruta.resolve()}"
            )

        try:
            with ruta.open(encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"El archivo '{ruta}' no es JSON válido.\n"
                f"  Detalle: {exc}"
            ) from exc

        self._config = raw
        self._ruta   = str(ruta)

        # Validar y lanzar todos los errores juntos
        errores = self._recopilar_errores()
        if errores:
            bloque = "\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errores))
            raise ConfigError(
                f"Se encontraron {len(errores)} error(es) en '{ruta}':\n{bloque}"
            )

        self._cargado = True

    # Acceso genérico
    def get(self, clave: str, default: Any = None) -> Any:
        """
        Acceso por clave con notación de punto: 'juego.velocidad_x_ms'.
        Retorna default si la clave no existe (nunca lanza KeyError).

        Ejemplo:
            config.get('juego.refresh_ms')       -> 200
            config.get('pantalla.ancho')          -> 1280
            config.get('inexistente', 0)          -> 0
        """
        self._verificar_cargado()
        partes  = clave.split(".")
        actual: Any = self._config
        for parte in partes:
            if not isinstance(actual, dict) or parte not in actual:
                return default
            actual = actual[parte]
        return actual

    def get_juego(self, clave: str, default: Any = None) -> Any:
        """Atajo para config.get(f'juego.{clave}', default)."""
        return self.get(f"juego.{clave}", default)

    def get_pantalla(self, clave: str, default: Any = None) -> Any:
        """Atajo para config.get(f'pantalla.{clave}', default)."""
        return self.get(f"pantalla.{clave}", default)

    # Obstáculos
    def obstaculos(self) -> list[Obstaculo]:
        """
        Retorna la lista de objetos Obstaculo construidos desde el JSON.
        Cada obstáculo ya tiene su `danio` tomado de tipos_obstaculo.
        Lista ordenada por x1 para facilitar debug (el AVL los reordena solo).

        Duplicados de coordenadas: se omiten con un aviso (el AVL los rechazaría igual).
        """
        self._verificar_cargado()

        tipos_cfg: dict = self._config.get("tipos_obstaculo", {})
        lista_raw: list = self._config.get("obstaculos", [])
        resultado: list[Obstaculo] = []
        vistas: set[tuple[int, int]] = set()

        for i, raw in enumerate(lista_raw):
            tipo_str = raw.get("tipo", "")
            x1, y1   = int(raw["x1"]), int(raw["y1"])
            x2, y2   = int(raw["x2"]), int(raw["y2"])

            clave = (x1, y1)
            if clave in vistas:
                print(
                    f"[ConfigLoader] AVISO: obstáculo #{i+1} ignorado — "
                    f"coordenada duplicada ({x1},{y1})"
                )
                continue
            vistas.add(clave)

            danio      = int(tipos_cfg[tipo_str]["danio"])
            tipo_enum  = TipoObstaculo(tipo_str)

            resultado.append(
                Obstaculo(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    tipo=tipo_enum,
                    danio=danio,
                )
            )

        return sorted(resultado, key=lambda o: (o.x1, o.y1))

    def tipos_obstaculo(self) -> dict[str, dict]:
        """Devuelve el dict completo de tipos_obstaculo del JSON."""
        self._verificar_cargado()
        return dict(self._config.get("tipos_obstaculo", {}))

    # Colores
    @staticmethod
    def hex_a_rgb(hex_color: str) -> tuple[int, int, int]:
        """
        Convierte '#RRGGBB' a (R, G, B).
        Lanza ValueError si el formato es inválido.

        Ejemplo: hex_a_rgb('#3A7BD5') -> (58, 123, 213)
        """
        if not _RE_HEX_COLOR.match(hex_color):
            raise ValueError(
                f"Color inválido: '{hex_color}'. Formato esperado: #RRGGBB"
            )
        h = hex_color.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def color_carrito(self) -> tuple[int, int, int]:
        return self.hex_a_rgb(self.get_juego("color_carrito", "#3A7BD5"))

    def color_salto(self) -> tuple[int, int, int]:
        return self.hex_a_rgb(self.get_juego("color_salto", "#F5A623"))

    def color_tipo(self, tipo: str) -> tuple[int, int, int]:
        """RGB del color de un tipo de obstáculo."""
        self._verificar_cargado()
        hex_c = self._config["tipos_obstaculo"][tipo]["color"]
        return self.hex_a_rgb(hex_c)

    # Validaciones internas
    def _recopilar_errores(self) -> list[str]:
        """
        Recorre el JSON y recopila TODOS los errores encontrados.
        Retorna lista de strings descriptivos. Lista vacía = JSON válido.

        Patrón "acumular antes de lanzar": el usuario ve todos sus errores
        de una vez en lugar de corregir uno por ejecución.
        """
        errores: list[str] = []

        errores += self._validar_seccion("juego",           self._reglas_juego())
        errores += self._validar_seccion("pantalla",        self._reglas_pantalla())
        errores += self._validar_tipos_obstaculo()
        errores += self._validar_obstaculos()

        return errores

    def _validar_seccion(
        self,
        seccion: str,
        reglas: list[tuple[str, type, Any, Any, str]],
    ) -> list[str]:
        """
        Valida una sección del JSON contra una lista de reglas.
        Cada regla: (clave, tipo_python, valor_min, valor_max, descripcion)
            - valor_min / valor_max = None significa sin límite.
        """
        errores: list[str] = []
        datos: dict = self._config.get(seccion, {})

        if not isinstance(datos, dict):
            return [f"'{seccion}' debe ser un objeto JSON, no {type(datos).__name__}"]

        for clave, tipo, vmin, vmax, desc in reglas:
            if clave not in datos:
                errores.append(f"'{seccion}.{clave}' es obligatorio ({desc})")
                continue

            valor = datos[clave]

            # Validar tipo
            if not isinstance(valor, tipo):
                errores.append(
                    f"'{seccion}.{clave}' debe ser {tipo.__name__}, "
                    f"se recibió {type(valor).__name__} = {valor!r}"
                )
                continue

            # Validar rango mínimo
            if vmin is not None and valor < vmin:
                errores.append(
                    f"'{seccion}.{clave}' debe ser >= {vmin}, se recibió {valor}"
                )

            # Validar rango máximo
            if vmax is not None and valor > vmax:
                errores.append(
                    f"'{seccion}.{clave}' debe ser <= {vmax}, se recibió {valor}"
                )

        return errores

    def _reglas_juego(self) -> list[tuple]:
        """
        Reglas de validación de la sección 'juego'.
        Formato: (clave, tipo, min, max, descripcion)
        """
        return [
            ("distancia_total_m", (int, float), 1,    None, "distancia total en metros > 0"),
            ("velocidad_x_ms",    (int, float), 0.1,  None, "metros avanzados por tick > 0"),
            ("velocidad_y_ms",    (int, float), 0.1,  None, "metros en Y por tick > 0"),
            ("refresh_ms",        (int, float), 16,   5000, "ms entre ticks logicos [16..5000]"),
            ("fuerza_salto",      (int, float), 0.1,  None, "velocidad inicial del salto > 0"),
            ("gravedad",          (int, float), 0.1,  None, "aceleracion gravitacional > 0"),
            ("energia_inicial",   (int,),        1,    100,  "energia inicial del carrito [1..100]"),
            ("pixels_por_metro",  (int, float), 1,    None, "escala de conversion metros->pixeles > 0"),
        ]

    def _reglas_pantalla(self) -> list[tuple]:
        return [
            ("ancho", (int,), 320, 7680, "ancho de pantalla en pixeles [320..7680]"),
            ("alto",  (int,), 240, 4320, "alto de pantalla en pixeles [240..4320]"),
        ]

    def _validar_tipos_obstaculo(self) -> list[str]:
        """Valida que existan todos los TipoObstaculo del enum y que sus campos sean correctos."""
        errores: list[str] = []
        tipos_cfg: dict = self._config.get("tipos_obstaculo", {})

        if not isinstance(tipos_cfg, dict):
            return ["'tipos_obstaculo' debe ser un objeto JSON"]

        tipos_validos = {t.value for t in TipoObstaculo}

        # Verificar que todos los tipos del enum estén presentes
        for tipo_val in tipos_validos:
            if tipo_val not in tipos_cfg:
                errores.append(
                    f"'tipos_obstaculo.{tipo_val}' es obligatorio pero falta en el JSON"
                )
                continue

            cfg_tipo = tipos_cfg[tipo_val]

            # Validar campo 'danio'
            if "danio" not in cfg_tipo:
                errores.append(f"'tipos_obstaculo.{tipo_val}.danio' es obligatorio")
            elif not isinstance(cfg_tipo["danio"], (int, float)):
                errores.append(
                    f"'tipos_obstaculo.{tipo_val}.danio' debe ser numérico, "
                    f"se recibió {type(cfg_tipo['danio']).__name__}"
                )
            elif cfg_tipo["danio"] < 0:
                errores.append(
                    f"'tipos_obstaculo.{tipo_val}.danio' no puede ser negativo "
                    f"({cfg_tipo['danio']})"
                )

            # Validar campo 'color'
            if "color" not in cfg_tipo:
                errores.append(f"'tipos_obstaculo.{tipo_val}.color' es obligatorio")
            elif not _RE_HEX_COLOR.match(str(cfg_tipo.get("color", ""))):
                errores.append(
                    f"'tipos_obstaculo.{tipo_val}.color' debe ser #RRGGBB, "
                    f"se recibió '{cfg_tipo.get('color')}'"
                )

        return errores

    def _validar_obstaculos(self) -> list[str]:
        """
        Valida cada obstáculo de la lista:
            - Campos obligatorios presentes.
            - Tipo existe en tipos_obstaculo del JSON.
            - x1 < x2 y y1 < y2.
            - Coordenadas dentro del rango [0, distancia_total_m].
            - Colores de los obstáculos válidos (verificados en _validar_tipos_obstaculo).
        No valida duplicados aquí: se avisa en obstaculos() al construirlos.
        """
        errores: list[str] = []
        lista: list = self._config.get("obstaculos", [])

        if not isinstance(lista, list):
            return ["'obstaculos' debe ser una lista JSON"]

        tipos_cfg   = self._config.get("tipos_obstaculo", {})
        dist_max    = self._config.get("juego", {}).get("distancia_total_m", None)
        campos_req  = ("tipo", "x1", "y1", "x2", "y2")

        for i, raw in enumerate(lista):
            etiqueta = f"obstaculos[{i}]"

            if not isinstance(raw, dict):
                errores.append(f"'{etiqueta}' debe ser un objeto JSON")
                continue

            # Campos obligatorios
            faltantes = [c for c in campos_req if c not in raw]
            if faltantes:
                errores.append(
                    f"'{etiqueta}' faltan campos obligatorios: {faltantes}"
                )
                continue

            tipo_str = raw["tipo"]

            # Tipo válido
            if tipo_str not in tipos_cfg:
                tipos_disponibles = list(tipos_cfg.keys())
                errores.append(
                    f"'{etiqueta}.tipo' = '{tipo_str}' no existe en tipos_obstaculo. "
                    f"Valores válidos: {tipos_disponibles}"
                )

            # Coordenadas numéricas
            coords = {k: raw[k] for k in ("x1", "y1", "x2", "y2")}
            no_numericos = [k for k, v in coords.items() if not isinstance(v, (int, float))]
            if no_numericos:
                errores.append(
                    f"'{etiqueta}' coordenadas deben ser numéricas: {no_numericos}"
                )
                continue

            x1, y1, x2, y2 = int(raw["x1"]), int(raw["y1"]), int(raw["x2"]), int(raw["y2"])

            # x1 < x2
            if x1 >= x2:
                errores.append(
                    f"'{etiqueta}' x1={x1} debe ser < x2={x2}"
                )

            # y1 < y2
            if y1 >= y2:
                errores.append(
                    f"'{etiqueta}' y1={y1} debe ser < y2={y2}"
                )

            # Coordenadas dentro del mapa
            if dist_max is not None and x1 < 0:
                errores.append(
                    f"'{etiqueta}' x1={x1} no puede ser negativo"
                )
            if dist_max is not None and x2 > dist_max:
                errores.append(
                    f"'{etiqueta}' x2={x2} excede distancia_total_m={dist_max}"
                )

        return errores

    # Helpers Internos
    def _validar_seccion(
        self,
        seccion: str,
        reglas: list[tuple],
    ) -> list[str]:
        errores: list[str] = []
        datos: dict = self._config.get(seccion, {})

        if not isinstance(datos, dict):
            return [f"'{seccion}' debe ser un objeto JSON, no {type(datos).__name__}"]

        for regla in reglas:
            clave, tipos, vmin, vmax, desc = regla
            # Normalizar tipos a tuple
            if not isinstance(tipos, tuple):
                tipos = (tipos,)

            if clave not in datos:
                errores.append(f"'{seccion}.{clave}' es obligatorio ({desc})")
                continue

            valor = datos[clave]

            if not isinstance(valor, tipos):
                nombres = "/".join(t.__name__ for t in tipos)
                errores.append(
                    f"'{seccion}.{clave}' debe ser {nombres}, "
                    f"se recibió {type(valor).__name__} = {valor!r}"
                )
                continue

            if vmin is not None and valor < vmin:
                errores.append(
                    f"'{seccion}.{clave}' debe ser >= {vmin}, se recibió {valor}"
                )
            if vmax is not None and valor > vmax:
                errores.append(
                    f"'{seccion}.{clave}' debe ser <= {vmax}, se recibió {valor}"
                )

        # Validar colores de la sección juego
        if seccion == "juego":
            for campo_color in ("color_carrito", "color_salto"):
                if campo_color not in datos:
                    errores.append(f"'juego.{campo_color}' es obligatorio")
                elif not _RE_HEX_COLOR.match(str(datos.get(campo_color, ""))):
                    errores.append(
                        f"'juego.{campo_color}' debe ser #RRGGBB, "
                        f"se recibió '{datos.get(campo_color)}'"
                    )

        return errores

    def _verificar_cargado(self) -> None:
        if not self._cargado:
            raise RuntimeError(
                "ConfigLoader: debes llamar a cargar(ruta) antes de acceder a la configuración."
            )

    # Representación
    def __repr__(self) -> str:
        estado = f"'{self._ruta}'" if self._cargado else "sin cargar"
        return f"ConfigLoader({estado})"

# Excepción Propia
class ConfigError(Exception):
    """
    Excepción lanzada cuando el JSON de configuración tiene errores.
    Contiene todos los problemas encontrados en un solo mensaje.
    """
    pass