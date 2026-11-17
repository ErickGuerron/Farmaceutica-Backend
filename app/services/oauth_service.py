"""Login con Google, Facebook e Instagram (flujo OAuth 2.0 con código de autorización).

El parámetro `state` es un JWT firmado con vencimiento corto: protege contra CSRF sin guardar estado en el servidor.
"""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import jwt
import requests

from app.config import Config
from app.errors import ErrorAplicacion
from app.models.usuario import PROVEEDORES

STATE_MINUTOS = 10
TIMEOUT = 10


def _redirect_uri(proveedor, config: Config):
    return f"{config.oauth_redirect_base}/auth/{proveedor}/callback"


def _credenciales(proveedor, config: Config):
    if proveedor == "google":
        cid, secreto = config.google_client_id, config.google_client_secret
    elif proveedor == "facebook":
        cid, secreto = config.facebook_app_id, config.facebook_app_secret
    else:
        cid, secreto = config.instagram_app_id, config.instagram_app_secret

    if not cid or not secreto:
        raise ErrorAplicacion(f"El login con {proveedor} no está configurado", status=503)
    return cid, secreto


def crear_state(proveedor, config: Config, flujo_web=False):
    ahora = datetime.now(timezone.utc)
    payload = {
        "prov": proveedor,
        "nonce": secrets.token_urlsafe(16),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=STATE_MINUTOS),
    }
    if flujo_web:
        payload["flujo"] = "flutter_web"
    return jwt.encode(payload, config.jwt_secret, algorithm="HS256")


def _validar_state(state, proveedor, config: Config):
    try:
        payload = jwt.decode(state, config.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise ErrorAplicacion("Estado de autorización inválido o vencido", status=400)
    if payload.get("prov") != proveedor:
        raise ErrorAplicacion("Estado de autorización inválido", status=400)
    return payload


def es_flujo_web(state, proveedor, config):
    if not state or proveedor not in PROVEEDORES:
        return False
    try:
        return _validar_state(state, proveedor, config).get("flujo") == "flutter_web"
    except ErrorAplicacion:
        return False  # El callback anterior conserva sus respuestas de validación.


def url_autorizacion(proveedor, config: Config, *, state=None):
    if proveedor not in PROVEEDORES:
        raise ErrorAplicacion("Proveedor no soportado", status=404)

    cid, _ = _credenciales(proveedor, config)
    state = state or crear_state(proveedor, config)
    redirect = _redirect_uri(proveedor, config)

    if proveedor == "google":
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": cid,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    elif proveedor == "facebook":
        base = f"https://www.facebook.com/{config.facebook_graph_version}/dialog/oauth"
        params = {
            "client_id": cid,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": "email,public_profile",
            "state": state,
        }
    else:
        # Instagram se autentica con Facebook Login: la cuenta profesional debe estar en una Página de Facebook.
        base = f"https://www.facebook.com/{config.facebook_graph_version}/dialog/oauth"
        params = {
            "client_id": cid,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": "instagram_basic,pages_show_list",
            "state": state,
        }

    return f"{base}?{urlencode(params)}"


def _llamar(metodo, url, **kwargs):
    try:
        respuesta = requests.request(metodo, url, timeout=TIMEOUT, **kwargs)
        respuesta.raise_for_status()
        return respuesta.json()
    except (requests.RequestException, ValueError):
        raise ErrorAplicacion("No se pudo validar la sesión con el proveedor", status=502)


def _perfil_google(code, config: Config):
    cid, secreto = _credenciales("google", config)
    token = _llamar("POST", "https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": cid,
        "client_secret": secreto,
        "redirect_uri": _redirect_uri("google", config),
        "grant_type": "authorization_code",
    })
    info = _llamar("GET", "https://openidconnect.googleapis.com/v1/userinfo",
                   headers={"Authorization": f"Bearer {token['access_token']}"})
    return {
        "uid": info["sub"],
        "nombre": info.get("name"),
        "email": info.get("email"),
        "email_verificado": bool(info.get("email_verified")),
    }


def _perfil_facebook(code, config: Config):
    cid, secreto = _credenciales("facebook", config)
    version = config.facebook_graph_version
    token = _llamar("GET", f"https://graph.facebook.com/{version}/oauth/access_token", params={
        "client_id": cid,
        "client_secret": secreto,
        "redirect_uri": _redirect_uri("facebook", config),
        "code": code,
    })
    info = _llamar("GET", f"https://graph.facebook.com/{version}/me", params={
        "fields": "id,name,email",
        "access_token": token["access_token"],
    })
    # Facebook solo entrega correos confirmados por el usuario.
    return {
        "uid": info["id"],
        "nombre": info.get("name"),
        "email": info.get("email"),
        "email_verificado": bool(info.get("email")),
    }


def _perfil_instagram(code, config: Config):
    """Flujo Instagram API with Facebook Login: token de usuario -> Páginas -> cuenta profesional de Instagram."""
    cid, secreto = _credenciales("instagram", config)
    version = config.facebook_graph_version

    token = _llamar("GET", f"https://graph.facebook.com/{version}/oauth/access_token", params={
        "client_id": cid,
        "client_secret": secreto,
        "redirect_uri": _redirect_uri("instagram", config),
        "code": code,
    })["access_token"]

    paginas = _llamar("GET", f"https://graph.facebook.com/{version}/me/accounts", params={
        "fields": "id,name,instagram_business_account",
        "access_token": token,
    }).get("data", [])

    cuenta = next((p["instagram_business_account"] for p in paginas if p.get("instagram_business_account")), None)
    if cuenta is None:
        raise ErrorAplicacion(
            "No se encontró una cuenta de Instagram profesional conectada a una Página de Facebook",
            status=400,
        )

    info = _llamar("GET", f"https://graph.facebook.com/{version}/{cuenta['id']}", params={
        "fields": "username",
        "access_token": token,
    })
    # Instagram no entrega correo: la cuenta se identifica por su ID de Instagram.
    return {
        "uid": cuenta["id"],
        "nombre": info.get("username"),
        "email": None,
        "email_verificado": False,
    }


def perfil_desde_callback(proveedor, code, state, config: Config):
    """Valida el state, intercambia el código y devuelve el perfil normalizado del proveedor."""
    if proveedor not in PROVEEDORES:
        raise ErrorAplicacion("Proveedor no soportado", status=404)
    if not code or not state:
        raise ErrorAplicacion("Falta el código de autorización", status=400)

    _validar_state(state, proveedor, config)
    # Instagram agrega "#_" al final del código; no forma parte del código.
    code = code.split("#")[0]

    perfil = {
        "google": _perfil_google,
        "facebook": _perfil_facebook,
        "instagram": _perfil_instagram,
    }[proveedor](code, config)

    if not perfil.get("uid"):
        raise ErrorAplicacion("El proveedor no devolvió un identificador de usuario", status=502)
    return perfil
