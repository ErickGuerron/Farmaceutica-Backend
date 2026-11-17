from datetime import datetime, timedelta, timezone

import jwt

from app.config import Config

ALGORITMO = "HS256"


def emitir_token(usuario: dict, config: Config):
    """usuario es el dict de usuario_service.serializar_usuario. Devuelve (token, segundos_de_vida)."""
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=config.jwt_expira_horas)
    payload = {
        "sub": str(usuario["id_usuario"]),
        "rol": usuario["rol"],
        "iat": ahora,
        "exp": expira,
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm=ALGORITMO)
    return token, int((expira - ahora).total_seconds())


def leer_token(token, config: Config):
    """Devuelve el payload o None si el token es inválido o expiró."""
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None
