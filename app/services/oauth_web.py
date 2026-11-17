import base64
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

from sqlalchemy import delete, insert, select, update

from app.database import engine
from app.errors import ErrorAplicacion
from app.models.oauth_web import intento_oauth_web as tabla


def _ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(valor):
    return hashlib.sha256(valor.encode("ascii")).hexdigest()


def crear(state, retorno, desafio, config):
    if retorno not in config.oauth_frontend_returns or len(retorno) > 1024:
        raise ErrorAplicacion("La URL de retorno de Flutter no está autorizada", status=400)
    url = urlsplit(retorno)
    es_local = url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}
    if not url.hostname or (url.scheme != "https" and not es_local) or url.username or url.query or url.fragment:
        raise ErrorAplicacion("La URL de retorno de Flutter no es válida", status=400)
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", desafio):
        raise ErrorAplicacion("El desafío del navegador no es válido", status=400)
    ahora = _ahora()
    with engine().begin() as conn:
        conn.execute(delete(tabla).where(tabla.c.expira <= ahora))
        conn.execute(insert(tabla).values(
            state_hash=_hash(state), desafio=desafio, retorno=retorno,
            fase="inicio", expira=ahora + timedelta(minutes=10),
        ))


def tomar_callback(state):
    llave = _hash(state)
    with engine().begin() as conn:
        tomado = conn.execute(update(tabla).where(
            tabla.c.state_hash == llave, tabla.c.fase == "inicio", tabla.c.expira > _ahora(),
        ).values(fase="procesando"))
        if tomado.rowcount != 1:
            raise ErrorAplicacion("El intento de inicio de sesión venció o ya fue utilizado", status=400)
        return conn.execute(select(tabla.c.retorno).where(tabla.c.state_hash == llave)).scalar_one()


def completar(state, id_usuario):
    codigo = secrets.token_urlsafe(32)
    ahora = _ahora()
    with engine().begin() as conn:
        listo = conn.execute(update(tabla).where(
            tabla.c.state_hash == _hash(state), tabla.c.fase == "procesando", tabla.c.expira > ahora,
        ).values(fase="listo", id_usuario=id_usuario, codigo_hash=_hash(codigo),
                 expira=ahora + timedelta(seconds=60)))
        if listo.rowcount != 1:
            raise ErrorAplicacion("El intento de inicio de sesión venció", status=400)
    return codigo


def intercambiar(state, codigo, verificador):
    if (not isinstance(state, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,1024}", state)
            or not isinstance(codigo, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", codigo)
            or not isinstance(verificador, str) or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verificador)):
        raise ErrorAplicacion("El código de acceso no es válido", status=400)
    digest = hashlib.sha256(verificador.encode("ascii")).digest()
    desafio = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    condicion = (
        tabla.c.state_hash == _hash(state), tabla.c.codigo_hash == _hash(codigo),
        tabla.c.fase == "listo", tabla.c.expira > _ahora(),
    )
    with engine().begin() as conn:
        intento = conn.execute(select(tabla.c.desafio, tabla.c.id_usuario).where(*condicion)).first()
        if intento and secrets.compare_digest(intento.desafio, desafio):
            if conn.execute(delete(tabla).where(*condicion)).rowcount == 1:
                return intento.id_usuario
    raise ErrorAplicacion("El código de acceso venció, ya se usó o no corresponde a esta pestaña", status=400)


def url_retorno(destino, state, **datos):
    return f"{destino}?{urlencode({'oauth_state': state, **datos})}"
