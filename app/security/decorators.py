from functools import wraps

from flask import current_app, g, jsonify, request

from app.models.usuario import ROL_ADMIN
from app.security.tokens import leer_token
from app.services.usuario_service import obtener_usuario


def _respuesta(mensaje, status):
    return jsonify({"mensaje": mensaje}), status


def _usuario_desde_token():
    """Devuelve (usuario, None) o (None, respuesta_de_error) a partir del encabezado Bearer."""
    encabezado = request.headers.get("Authorization", "")
    partes = encabezado.split()
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return None, _respuesta("Debe iniciar sesión", 401)

    payload = leer_token(partes[1], current_app.config["SETTINGS"])
    if payload is None:
        return None, _respuesta("Sesión inválida o expirada", 401)

    usuario = obtener_usuario(int(payload["sub"]))
    if usuario is None or not usuario["activo"]:
        return None, _respuesta("Sesión inválida o expirada", 401)

    return usuario, None


def requiere_rol(*roles):
    """Exige sesión y que el rol del usuario esté entre `roles`.

    El rol se lee de la base de datos en cada petición, así un cambio de rol surte efecto de inmediato.
    """
    def decorador(f):
        @wraps(f)
        def envoltura(*args, **kwargs):
            usuario, error = _usuario_desde_token()
            if error is not None:
                return error
            if usuario["rol"] not in roles:
                return _respuesta("No tiene permisos para esta operación", 403)
            g.usuario = usuario
            return f(*args, **kwargs)
        return envoltura
    return decorador


# Lectura: admin o empleado. Escritura: solo admin.
requiere_lectura_empleados = requiere_rol(ROL_ADMIN, "empleado")
requiere_admin = requiere_rol(ROL_ADMIN)
