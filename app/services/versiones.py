import base64


def codificar_version(version):
    """Convierte el rowversion binario en texto base64 para el cliente."""
    return base64.b64encode(version).decode("utf-8")


def decodificar_version(version):
    """Devuelve los bytes del rowversion o None si el texto no es base64 válido."""
    try:
        return base64.b64decode(version, validate=True)
    except Exception:
        return None
