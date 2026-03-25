"""
main.py — Punto de entrada para la simulación CLI (Fase 3).

Uso:
    python main.py                          # modo headless rápido
    python main.py --verbose                # log tick a tick
    python main.py --interactivo            # modo con teclado (solo UNIX)
    python main.py --config otra_config.json
    python main.py --velocidad 5.0          # 5× más rápido
    python main.py --acciones "10:saltar,20:arriba,40:saltar"

El modo headless ejecuta la simulación sin input del usuario, lo que
permite verificar la lógica de colisiones, energía y condición de fin
de manera automatizada (ideal para CI/CD y demostraciones).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

def parsear_acciones(texto: str) -> list[tuple[int, str]]:
    """
    Convierte "10:saltar,20:arriba" en [(10, 'saltar'), (20, 'arriba')].
    Acciones válidas: saltar, arriba, abajo.
    """
    acciones = []
    for parte in texto.split(","):
        parte = parte.strip()
        if ":" not in parte:
            continue
        tick_str, accion = parte.split(":", 1)
        try:
            tick = int(tick_str.strip())
            acciones.append((tick, accion.strip().lower()))
        except ValueError:
            print(f"  [main] Acción ignorada (formato inválido): '{parte}'")
    return acciones

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Carrito AVL Runner — Simulación CLI (Fase 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
    python main.py
    python main.py --verbose
    python main.py --velocidad 10 --verbose
    python main.py --acciones "5:saltar,15:abajo,30:saltar"
    python main.py --interactivo
        """,
    )
    parser.add_argument(
        "--config",
        default="config/game_config.json",
        help="Ruta al archivo JSON de configuración (default: config/game_config.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar log tick a tick (sin limpiar pantalla)",
    )
    parser.add_argument(
        "--interactivo", "-i",
        action="store_true",
        help="Modo interactivo con teclado (solo UNIX con TTY)",
    )
    parser.add_argument(
        "--velocidad",
        type=float,
        default=50.0,
        help="Multiplicador de velocidad de simulación (default: 50× para demo rápida)",
    )
    parser.add_argument(
        "--acciones",
        type=str,
        default="",
        help="Acciones programadas: 'tick:accion,...' (ej: '5:saltar,20:abajo')",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Número máximo de ticks antes de detener la simulación",
    )

    args = parser.parse_args()

    # Verificar que el archivo de config existe
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"\n Archivo de configuración no encontrado: '{config_path}'")
        print(f"     Ejecuta el script desde el directorio raíz del proyecto.\n")
        return 1

    # Importar aquí para que los errores de import sean claros
    try:
        from engine.game_engine import GameEngine
        from core.enums import GameState
    except ImportError as e:
        print(f"\n  ❌ Error de importación: {e}")
        print("     Asegúrate de ejecutar desde el directorio raíz del proyecto.\n")
        return 1

    # Parsear acciones programadas
    acciones = parsear_acciones(args.acciones) if args.acciones else None

    # Crear y ejecutar el engine
    engine = GameEngine(
        ruta_config=config_path,
        verbose=args.verbose,
        velocidad_simulacion=args.velocidad,
    )

    if args.interactivo:
        estado_final = engine.run()
    else:
        estado_final = engine.run_headless(
            acciones=acciones,
            max_ticks=args.max_ticks,
        )

    # Código de salida: 0 = victoria, 1 = derrota
    return 0 if estado_final == GameState.VICTORIA else 1

if __name__ == "__main__":
    sys.exit(main())