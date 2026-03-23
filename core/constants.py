"""
Constantes globales de pantalla y juego. Sin dependencias externas.
"""

# Pantalla
SCREEN_W: int = 1280
SCREEN_H: int = 720
FPS:      int = 60       # FPS de renderizado (Pygame)
TITULO:   str = "Carrito AVL Runner"

# Cámara
CAMARA_OFFSET_X: int = 120   # píxeles desde el borde izq donde aparece el carrito

# Carriles Y (en píxeles)
CARRIL_TOP: int = 180
CARRIL_MID: int = 360
CARRIL_BOT: int = 540

# Escala
PIXELS_POR_METRO: int = 10   # 1 metro = 10 píxeles en eje X

# Colores por defecto del carrito
COLOR_CARRITO_DEFAULT: tuple = (58, 123, 213)    # azul
COLOR_SALTO_DEFAULT:   tuple = (245, 166, 35)    # naranja

# Colores de tipos de obstáculo (fallback)
COLORES_OBSTACULOS: dict = {
    "ROCA":   (90,  90,  90),
    "BARRIL": (232, 119, 34),
    "CHARCO": (26,  58,  92),
    "MURO":   (194, 181, 155),
    "CONO":   (255, 107, 53),
}