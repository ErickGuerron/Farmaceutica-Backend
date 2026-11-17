from flask import Blueprint, current_app, g, jsonify, redirect, request

from app.errors import ErrorAplicacion
from app.models.usuario import ROL_EMPLEADO
from app.security.decorators import requiere_admin, requiere_rol
from app.security.tokens import emitir_token
from app.services import oauth_service, oauth_web, usuario_service

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
    retorno = request.args.get("retorno")
    if retorno is not None:
        state = oauth_service.crear_state(proveedor, _config(), flujo_web=True)
        url = oauth_service.url_autorizacion(proveedor, _config(), state=state)
        oauth_web.crear(state, retorno, request.args.get("desafio", ""), _config())
        return _sin_cache(jsonify({"authorization_url": url, "state": state}))
    url = oauth_service.url_autorizacion(proveedor, _config())
    return jsonify({"authorization_url": url}), 200


@bp.route("/<proveedor>/callback", methods=["GET"])
def callback_oauth(proveedor):
    state = request.args.get("state")
    if oauth_service.es_flujo_web(state, proveedor, _config()):
        retorno = oauth_web.tomar_callback(state)
        try:
            if request.args.get("error"):
                return _sin_cache(redirect(oauth_web.url_retorno(retorno, state, oauth_error="cancelado"), 303))
            usuario = _usuario_oauth(proveedor)
            codigo = oauth_web.completar(state, usuario["id_usuario"])
        except ErrorAplicacion:
            return _sin_cache(redirect(oauth_web.url_retorno(retorno, state, oauth_error="acceso_fallido"), 303))
        return _sin_cache(redirect(oauth_web.url_retorno(retorno, state, oauth_code=codigo), 303))

    if request.args.get("error"):
        raise ErrorAplicacion("El inicio de sesión fue cancelado o denegado", status=400)
    return jsonify(_respuesta_token(_usuario_oauth(proveedor))), 200


def _usuario_oauth(proveedor):
    perfil_proveedor = oauth_service.perfil_desde_callback(
        proveedor,
        request.args.get("code"),
        request.args.get("state"),
        _config(),
    )

    return usuario_service.login_oauth(
        proveedor,
        perfil_proveedor["uid"],
        perfil_proveedor.get("nombre"),
        perfil_proveedor.get("email"),
        perfil_proveedor.get("email_verificado", False),
    )


def _sin_cache(respuesta):
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    return respuesta


@bp.route("/intercambiar", methods=["POST"])
def intercambiar_oauth():
    data = _json_requerido()
    id_usuario = oauth_web.intercambiar(data.get("state"), data.get("code"), data.get("verifier"))
    usuario = usuario_service.obtener_usuario(id_usuario)
    if usuario is None or not usuario["activo"]:
        raise ErrorAplicacion("La cuenta está desactivada", status=403)
    return _sin_cache(jsonify(_respuesta_token(usuario)))


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
