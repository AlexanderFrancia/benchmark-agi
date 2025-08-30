from django import template

register = template.Library()

# Paleta ARC típica (puedes ajustarla)
PALETTE = {
    0: "#000000",  # negro
    1: "#1E90FF",  # azul
    2: "#FF4136",  # rojo
    3: "#2ECC40",  # verde
    4: "#FFDC00",  # amarillo
    5: "#AAAAAA",  # gris
    6: "#F012BE",  # magenta
    7: "#FF851B",  # naranja
    8: "#39CCCC",  # cian
    9: "#8B4513",  # marrón
}

@register.filter(name="cell_color")
def cell_color(v):
    """
    Devuelve el color HEX para el valor entero v.
    Si no existe en la paleta, usa gris claro.
    """
    try:
        return PALETTE.get(int(v), "#DDDDDD")
    except (ValueError, TypeError):
        return "#DDDDDD"
