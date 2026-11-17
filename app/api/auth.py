from flask import Blueprint, current_app, g, jsonify, request

from app.errors import ErrorAplicacion
from app.models.usuario import ROL_EMPLEADO
from app.security.decorators import requiere_admin, requiere_rol
from app.security.tokens import emitir_token
from app.services import oauth_service, usuario_service

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _config():
    return current_app.config["SETTINGS"]


def _respuesta_token(usuario):
    token, expira_en = emitir_token(usuario, _config())
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expira_en,
        "usuario": usuario,
    }


def _json_requerido():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ErrorAplicacion("Debe enviar un cuerpo JSON válido")
    return data


@bp.route("/registro", methods=["POST"])
def registro():
    data = _json_requerido()
    nombre = (data.get("nombre") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not nombre or not email or len(password) < 8:
        raise ErrorAplicacion("Debe enviar nombre, email y una contraseña de al menos 8 caracteres")

    usuario = usuario_service.registrar_local(nombre, email, password, ROL_EMPLEADO)
    return jsonify({"mensaje": "Usuario registrado correctamente", "usuario": usuario}), 201


@bp.route("/login", methods=["POST"])
def login():
    data = _json_requerido()
    usuario = usuario_service.autenticar(data.get("email"), data.get("password"))
    if usuario is None:
        return jsonify({"mensaje": "Correo o contraseña incorrectos"}), 401
    return jsonify(_respuesta_token(usuario)), 200


@bp.route("/me", methods=["GET"])
@requiere_rol("admin", "empleado")
def perfil():
    return jsonify(g.usuario), 200


@bp.route("/<proveedor>/login", methods=["GET"])
def login_oauth(proveedor):
    url = oauth_service.url_autorizacion(proveedor, _config())
    return jsonify({"authorization_url": url}), 200


@bp.route("/<proveedor>/callback", methods=["GET"])
def callback_oauth(proveedor):
    if request.args.get("error"):
        raise ErrorAplicacion("El inicio de sesión fue cancelado o denegado", status=400)

    perfil_proveedor = oauth_service.perfil_desde_callback(
        proveedor,
        request.args.get("code"),
        request.args.get("state"),
        _config(),
    )

    usuario = usuario_service.login_oauth(
        proveedor,
        perfil_proveedor["uid"],
        perfil_proveedor.get("nombre"),
        perfil_proveedor.get("email"),
        perfil_proveedor.get("email_verificado", False),
    )
    return jsonify(_respuesta_token(usuario)), 200


# Administración de usuarios y roles (solo admin)

@bp.route("/usuarios", methods=["GET"])
@requiere_admin
def listar_usuarios():
    return jsonify(usuario_service.listar_usuarios()), 200


@bp.route("/usuarios/<int:id>/rol", methods=["PUT"])
@requiere_admin
def cambiar_rol(id):
    data = _json_requerido()
    usuario = usuario_service.asignar_rol(id, data.get("rol"))
    return jsonify({"mensaje": "Rol actualizado correctamente", "usuario": usuario}), 200
